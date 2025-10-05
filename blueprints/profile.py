"""
用户资料和设置功能蓝图
包含：宝宝资料管理、头像上传、封面设置等功能
"""
import os
import json
from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

# 创建蓝图
profile_bp = Blueprint('profile', __name__)

def _last_day_of_month(y: int, m: int) -> int:
    # 获取某月最后一天
    d = date(y, m, 28) + timedelta(days=4)
    d = d.replace(day=1) - timedelta(days=1)
    return d.day

def _add_months(d: date, months: int) -> date:
    # 将日期加上指定月数（若目标月没有该日，则取该月最后一天）
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, _last_day_of_month(y, m))
    return date(y, m, day)

def calc_age_months(birth: date, today: date | None = None) -> int:
    if not birth:
        return 0
    if today is None:
        today = date.today()
    months = (today.year - birth.year) * 12 + (today.month - birth.month)
    if today.day < birth.day:
        months -= 1
    return max(0, months)

def instance_file(pathname: str) -> str:
    inst = current_app.instance_path
    try:
        os.makedirs(inst, exist_ok=True)
    except Exception:
        pass
    return os.path.join(inst, pathname)

def load_profile() -> dict:
    import json
    p = instance_file('profile.json')
    if os.path.exists(p):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except Exception:
            return {}
    return {}

def save_profile(data: dict) -> None:
    import json
    p = instance_file('profile.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@profile_bp.post('/profile')
def update_profile():
    name = request.form.get('baby_name', '').strip()
    birth = request.form.get('baby_birth', '').strip()
    # 简单校验 YYYY-MM-DD
    if birth:
        try:
            y, m, d = [int(x) for x in birth.split('-')]
            _ = date(y, m, d)
        except Exception:
            flash('生日格式应为 YYYY-MM-DD', 'warning')
            return redirect(request.referrer or url_for('main.index'))
    try:
        prof = load_profile()
        prof['name'] = name
        prof['birth'] = birth
        save_profile(prof)
        flash('宝宝资料已保存', 'success')
    except Exception as exc:
        flash('保存失败：' + str(exc), 'danger')
    return redirect(request.referrer or url_for('main.index'))

@profile_bp.get('/settings')
def settings():
    # 直接渲染，模板可使用注入的 baby_* 变量
    return render_template('settings.html')

@profile_bp.post('/avatar/upload')
def upload_avatar():
    f = request.files.get('avatar')
    if not f or f.filename == '':
        flash('未选择图片', 'warning')
        return redirect(request.referrer or url_for('main.index'))
    # 校验扩展名
    filename = f.filename.lower()
    ext = None
    for e in ('jpg', 'jpeg', 'png'):
        if filename.endswith('.' + e):
            ext = e
            break
    if not ext:
        flash('仅支持 JPG/PNG 图片', 'warning')
        return redirect(request.referrer or url_for('main.index'))
    # 保存到 static 下的固定文件名
    target_name = 'avatar.jpg' if ext in ('jpg', 'jpeg') else 'avatar.png'
    try:
        save_path = os.path.join(current_app.static_folder or 'static', target_name)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        f.save(save_path)
        flash('头像已更新', 'success')
    except Exception as exc:
        flash('头像更新失败：' + str(exc), 'danger')
    return redirect(request.referrer or url_for('main.index'))

@profile_bp.post('/cover/upload')
def upload_cover():
    f = request.files.get('cover')
    if not f or f.filename == '':
        flash('未选择封面图片', 'warning')
        return redirect(request.referrer or url_for('main.index'))
    filename = f.filename.lower()
    ext = None
    for e in ('jpg', 'jpeg', 'png'):
        if filename.endswith('.' + e):
            ext = e
            break
    if not ext:
        flash('仅支持 JPG/PNG 图片', 'warning')
        return redirect(request.referrer or url_for('main.index'))
    try:
        from PIL import Image
        import io
        img = Image.open(f.stream).convert('RGB')
        # 等比缩放到最大宽度 1920（高度按比例），超大图降采样
        max_w = int(os.environ.get('COVER_MAX_WIDTH', '1920'))
        if img.width > max_w:
            ratio = max_w / float(img.width)
            new_size = (max_w, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        # 输出为 WebP（若需要可改为高压 JPG）
        out_path = os.path.join(current_app.static_folder or 'static', 'cover.webp')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        img.save(out_path, format='WEBP', quality=int(os.environ.get('COVER_QUALITY', '85')))
        flash('封面已更新并压缩为 WebP', 'success')
    except Exception as exc:
        flash('封面更新失败：' + str(exc), 'danger')
    return redirect(request.referrer or url_for('main.index'))
