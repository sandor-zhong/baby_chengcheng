"""
静态资源工具模块
"""
import os
from datetime import date
from flask import url_for
from utils.time_utils import calc_age_months, add_months


def get_avatar_url(app) -> str:
    """获取头像URL"""
    # 优先使用环境变量 AVATAR_URL（可为绝对 URL）
    env_url = os.environ.get('AVATAR_URL')
    if env_url:
        return env_url
    
    # 其次检测 static 下是否有用户自定义头像
    static_dir = app.static_folder or 'static'
    for fname in ['avatar.jpg', 'avatar.png', 'avatar.jpeg']:
        candidate = os.path.join(static_dir, fname)
        if os.path.exists(candidate):
            try:
                v = int(os.path.getmtime(candidate))
            except Exception:
                v = 0
            return url_for('static', filename=fname) + f'?v={v}'
    
    # 默认占位图
    try:
        v = int(os.path.getmtime(os.path.join(static_dir, 'avatar-default.svg')))
    except Exception:
        v = 0
    return url_for('static', filename='avatar-default.svg') + f'?v={v}'


def get_cover_url(app) -> str:
    """获取封面URL"""
    cover_env = os.environ.get('COVER_URL')
    if cover_env:
        return cover_env
    
    static_dir = app.static_folder or 'static'
    for fname in ['cover.jpg', 'cover.png', 'cover.jpeg']:
        candidate = os.path.join(static_dir, fname)
        if os.path.exists(candidate):
            try:
                v = int(os.path.getmtime(candidate))
            except Exception:
                v = 0
            return url_for('static', filename=fname) + f'?v={v}'
    
    # 默认封面
    try:
        v = int(os.path.getmtime(os.path.join(static_dir, 'cover-default.jpg')))
    except Exception:
        v = 0
    cover_url = url_for('static', filename='cover-default.jpg') + f'?v={v}'
    
    # 若存在压缩后的 cover.webp 优先使用
    try:
        v_webp = int(os.path.getmtime(os.path.join(static_dir, 'cover.webp')))
        cover_url = url_for('static', filename='cover.webp') + f'?v={v_webp}'
    except Exception:
        pass
    
    return cover_url


def get_profile_context(app) -> dict:
    """获取用户资料上下文"""
    from blueprints.profile import load_profile
    
    prof = load_profile()
    cover_url = get_cover_url(app)
    
    name = prof.get('name') or ''
    birth_str = prof.get('birth') or ''  # YYYY-MM-DD
    age_months = 0
    age_text = ''
    
    if birth_str:
        try:
            y, m, d = [int(x) for x in birth_str.split('-')]
            b = date(y, m, d)
            age_months = calc_age_months(b)
            years = age_months // 12
            months = age_months % 12
            
            # 计算剩余天数：从出生加上 age_months 月到今天的天数
            anchor = add_months(b, age_months)
            days = (date.today() - anchor).days
            days = max(0, days)
            
            # 组装年龄文案（精确到天），省略为 0 的单位
            parts = []
            if years:
                parts.append(f"{years}岁")
            if months:
                parts.append(f"{months}个月")
            parts.append(f"{days}天")
            age_text = ''.join(parts)
        except Exception:
            pass
    
    return {
        'baby_name': name,
        'baby_birth': birth_str,
        'baby_age_months': age_months,
        'baby_age_text': age_text,
        'cover_url': cover_url,
    }
