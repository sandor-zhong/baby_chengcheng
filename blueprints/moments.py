"""
时光记录功能蓝图
包含：时光发布、查看、编辑、删除、收藏等功能
"""
import os
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from models import db, Moment
from sqlalchemy import or_

# 创建蓝图
moments_bp = Blueprint('moments', __name__)
from utils.decorators import login_required

def get_date_label(d: date) -> str:
    """获取日期标签"""
    today_d = date.today()
    yesterday_d = today_d - timedelta(days=1)

    if d == today_d:
        return '今天'
    if d == yesterday_d:
        return '昨天'
    return d.strftime('%m月%d日')

@moments_bp.route('/moments')
def moments():
    """时光页面 - 类似朋友圈，支持懒加载"""
    from flask import session
    uid = session.get('uid')
    if not uid:
        # 未登录时返回空列表
        return render_template('moments.html', moments=[], has_prev=False, has_next=False, 
                             prev_num=None, next_num=None, page=1, pages=0, per_page=10)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    favorite_only = request.args.get('favorite', 'false').lower() == 'true'
    
    # 构建查询 - 只查询当前用户的数据
    query = Moment.query.filter(Moment.user_id == uid)
    
    # 如果只显示收藏
    if favorite_only:
        query = query.filter(Moment.is_favorite == True)
    
    # 使用索引优化查询
    moments = query.order_by(Moment.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # 构建日期分组：今天/昨天/具体日期
    today_d = date.today()
    yesterday_d = today_d - timedelta(days=1)
    def label_for(d: date) -> str:
        if d == today_d:
            return '今天'
        if d == yesterday_d:
            return '昨天'
        return d.strftime('%m月%d日')

    groups = []
    last_label = None
    for m in moments.items:
        d = (m.timestamp.date())
        label = label_for(d)
        if label != last_label:
            groups.append({'label': label, 'items': []})
            last_label = label
        groups[-1]['items'].append(m)

    return render_template('moments.html', moments=moments, groups=groups, 
                         favorite_only=favorite_only, per_page=per_page)

@moments_bp.route('/api/moments/load')
def load_moments_api():
    """懒加载时光API"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    favorite_only = request.args.get('favorite', 'false').lower() == 'true'
    
    # 构建查询
    from flask import session
    uid = session.get('uid')
    query = Moment.query
    if uid:
        query = query.filter(Moment.user_id == uid)
    
    if favorite_only:
        query = query.filter(Moment.is_favorite == True)
    
    moments = query.order_by(Moment.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 返回JSON格式数据
    moments_data = []
    for moment in moments.items:
        moments_data.append({
            'id': moment.id,
            'content': moment.content,
            'image_path': moment.image_path,
            'thumb_path': moment.thumb_path,
            'video_path': moment.video_path,
            'is_favorite': moment.is_favorite,
            'timestamp': moment.timestamp.isoformat(),
            'date_label': get_date_label(moment.timestamp.date())
        })
    
    return jsonify({
        'moments': moments_data,
        'has_next': moments.has_next,
        'has_prev': moments.has_prev,
        'current_page': moments.page,
        'total_pages': moments.pages
    })

@moments_bp.route('/api/moments/search')
def search_moments():
    """搜索时光API"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    if not query:
        return jsonify({'moments': [], 'total': 0, 'message': '请输入搜索关键词'})
    
    # 使用全文搜索
    from flask import session
    uid = session.get('uid')
    base = Moment.query
    if uid:
        base = base.filter(Moment.user_id == uid)
    search_query = base.filter(
        or_(
            Moment.content.contains(query),
            Moment.content.like(f'%{query}%')
        )
    ).order_by(Moment.timestamp.desc())
    
    moments = search_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    moments_data = []
    for moment in moments.items:
        moments_data.append({
            'id': moment.id,
            'content': moment.content,
            'image_path': moment.image_path,
            'thumb_path': moment.thumb_path,
            'video_path': moment.video_path,
            'is_favorite': moment.is_favorite,
            'timestamp': moment.timestamp.isoformat(),
            'date_label': get_date_label(moment.timestamp.date())
        })
    
    return jsonify({
        'moments': moments_data,
        'total': moments.total,
        'has_next': moments.has_next,
        'has_prev': moments.has_prev,
        'current_page': moments.page,
        'total_pages': moments.pages,
        'query': query
    })

@moments_bp.route('/moments/create', methods=['GET', 'POST'])
@login_required
def create_moment():
    """发布时光"""
    if request.method == 'GET':
        return render_template('create_moment.html')

    try:
        content = request.form.get('content', '').strip()
        if not content:
            flash('请输入内容', 'warning')
            return redirect(url_for('moments.create_moment'))

        image_path = None
        video_path = None
        thumb_path = None
        # 兼容旧字段 image；优先新字段 media
        file = request.files.get('media') or request.files.get('image')
        if file and file.filename:
            if file.mimetype and file.mimetype.startswith('video/'):
                # 保存视频并生成缩略图
                video_path, video_thumb = save_moment_video(file)
                thumb_path = video_thumb
            else:
                # 保存并压缩图片
                image_path = save_moment_image(file)
                # 生成缩略图
                if image_path:
                    try:
                        from PIL import Image
                        img_path = os.path.join(current_app.static_folder or 'static', image_path)
                        with Image.open(img_path) as img:
                            # 生成缩略图
                            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                            thumb_filename = f"thumb_{os.path.basename(image_path).replace('.webp', '')}.webp"
                            thumb_path = os.path.join(os.path.dirname(img_path), thumb_filename)
                            img.save(thumb_path, 'WEBP', quality=85, optimize=True)
                            thumb_path = f'moments/{thumb_filename}'
                    except Exception as e:
                        print(f"缩略图生成失败: {e}")
                        thumb_path = None

        from flask import session
        uid = session.get('uid')
        moment = Moment(content=content, image_path=image_path, thumb_path=thumb_path, video_path=video_path, user_id=uid)
        db.session.add(moment)
        db.session.commit()

        flash('发布成功！', 'success')
        return redirect(url_for('moments.moments'))

    except Exception as e:
        flash(f'发布失败：{str(e)}', 'danger')
        return redirect(url_for('moments.create_moment'))

@moments_bp.route('/moments/<int:moment_id>/delete', methods=['POST'])
@login_required
def delete_moment(moment_id):
    """删除时光"""
    from flask import session
    uid = session.get('uid')
    try:
        moment = Moment.query.filter(Moment.user_id == uid, Moment.id == moment_id).first_or_404()
        # 删除图片文件
        if moment.image_path and os.path.exists(moment.image_path):
            os.remove(moment.image_path)
        db.session.delete(moment)
        db.session.commit()
        flash('删除成功', 'success')
    except Exception as e:
        flash(f'删除失败：{str(e)}', 'danger')
    return redirect(url_for('moments.moments'))

@moments_bp.route('/moments/<int:moment_id>')
def moment_detail(moment_id: int):
    """时光详情页（查看，不编辑）"""
    from flask import session, flash, redirect, url_for
    uid = session.get('uid')
    if not uid:
        flash('请先登录', 'warning')
        return redirect(url_for('auth.login_page'))
    
    moment = Moment.query.filter(Moment.user_id == uid, Moment.id == moment_id).first_or_404()
    
    # 上下条（同页内，只查询当前用户的）
    prev_m = (
        Moment.query.filter(Moment.user_id == uid, Moment.timestamp > moment.timestamp)
        .order_by(Moment.timestamp.asc())
        .first()
    )
    next_m = (
        Moment.query.filter(Moment.user_id == uid, Moment.timestamp < moment.timestamp)
        .order_by(Moment.timestamp.desc())
        .first()
    )
    return render_template('moment_detail.html', moment=moment, prev_m=prev_m, next_m=next_m)

@moments_bp.route('/moments/<int:moment_id>/favorite', methods=['POST'])
def toggle_favorite(moment_id: int):
    """切换收藏状态"""
    from flask import session
    uid = session.get('uid')
    if not uid:
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    moment = Moment.query.filter(Moment.user_id == uid, Moment.id == moment_id).first_or_404()
    moment.is_favorite = not moment.is_favorite
    db.session.commit()
    return jsonify({'success': True, 'is_favorite': moment.is_favorite})

@moments_bp.route('/moments/<int:moment_id>/share')
def share_moment(moment_id: int):
    """分享时光"""
    from flask import session, jsonify
    uid = session.get('uid')
    if not uid:
        return jsonify({'success': False, 'error': '请先登录'}), 401
    
    moment = Moment.query.filter(Moment.user_id == uid, Moment.id == moment_id).first_or_404()
    # 生成分享链接
    share_url = request.url_root + url_for('moments.moment_detail', moment_id=moment_id)
    return jsonify({
        'success': True,
        'share_url': share_url,
        'title': f'宝宝时光 - {moment.timestamp.strftime("%Y-%m-%d %H:%M")}',
        'description': moment.content[:100] + '...' if len(moment.content) > 100 else moment.content
    })

@moments_bp.route('/moments/<int:moment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_moment(moment_id):
    """编辑时光"""
    from flask import session
    uid = session.get('uid')
    moment = Moment.query.filter(Moment.user_id == uid, Moment.id == moment_id).first_or_404()
    if request.method == 'GET':
        return render_template('edit_moment.html', moment=moment)
    try:
        content = request.form.get('content', '').strip()
        if not content:
            flash('内容不能为空', 'warning')
            return redirect(url_for('moments.edit_moment', moment_id=moment_id))

        # 更新文字
        moment.content = content

        # 如上传新图则替换并删除旧图
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename:
                new_path = save_moment_image(f)
                # 删除旧文件
                try:
                    if moment.image_path and os.path.exists(os.path.join(current_app.static_folder or 'static', moment.image_path)):
                        os.remove(os.path.join(current_app.static_folder or 'static', moment.image_path))
                except Exception:
                    pass
                moment.image_path = new_path
                # 同步更新缩略图路径（若存在）
                try:
                    base = os.path.basename(new_path) if new_path else None
                    if base and base.endswith('.webp'):
                        name = base[:-5]
                        thumb_candidate = os.path.join(current_app.static_folder or 'static', 'moments', name + '_thumb.webp')
                        if os.path.exists(thumb_candidate):
                            moment.thumb_path = 'moments/' + name + '_thumb.webp'
                except Exception:
                    pass

        db.session.commit()
        flash('已保存修改', 'success')
        return redirect(url_for('moments.moments'))
    except Exception as exc:
        db.session.rollback()
        flash('保存失败：' + str(exc), 'danger')
        return redirect(url_for('moments.edit_moment', moment_id=moment_id))

def save_moment_image(image_file):
    """保存并压缩时光图片"""
    try:
        from PIL import Image
        import io

        # 创建时光图片目录
        moments_dir = os.path.join(current_app.static_folder or 'static', 'moments')
        os.makedirs(moments_dir, exist_ok=True)

        # 打开并处理图片
        img = Image.open(image_file.stream).convert('RGB')

        # 压缩到合适尺寸
        max_width = 800
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'moment_{timestamp}.webp'
        filepath = os.path.join(moments_dir, filename)

        # 保存为WebP格式（主图）
        img.save(filepath, format='WEBP', quality=85)

        # 生成缩略图（列表用）
        thumb_w = 360
        thumb = img.copy()
        if thumb.width > thumb_w:
            r = thumb_w / float(thumb.width)
            thumb = thumb.resize((thumb_w, int(thumb.height * r)), Image.LANCZOS)
        thumb_filename = f'moment_{timestamp}_thumb.webp'
        thumb_filepath = os.path.join(moments_dir, thumb_filename)
        thumb.save(thumb_filepath, format='WEBP', quality=80)

        return f'moments/{filename}'

    except Exception as e:
        raise Exception(f'图片处理失败：{str(e)}')

def save_moment_video(video_file):
    """保存视频文件并生成缩略图"""
    try:
        from PIL import Image
        try:
            import cv2
        except ImportError:
            # 如果没有cv2，直接保存视频不生成缩略图
            moments_dir = os.path.join(current_app.static_folder or 'static', 'moments')
            os.makedirs(moments_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_filename = f'moment_{timestamp}.mp4'
            video_filepath = os.path.join(moments_dir, video_filename)
            video_file.save(video_filepath)
            return f'moments/{video_filename}', None
        
        moments_dir = os.path.join(current_app.static_folder or 'static', 'moments')
        os.makedirs(moments_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存视频
        video_filename = f'moment_{timestamp}.mp4'
        video_filepath = os.path.join(moments_dir, video_filename)
        video_file.save(video_filepath)
        
        # 生成视频缩略图
        try:
            cap = cv2.VideoCapture(video_filepath)
            ret, frame = cap.read()
            if ret:
                # 转换为RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 创建PIL图像
                pil_image = Image.fromarray(frame_rgb)
                # 生成缩略图
                thumb_filename = f'moment_{timestamp}_thumb.webp'
                thumb_filepath = os.path.join(moments_dir, thumb_filename)
                pil_image.save(thumb_filepath, 'WEBP', quality=85, optimize=True)
                cap.release()
                return f'moments/{video_filename}', f'moments/{thumb_filename}'
            else:
                cap.release()
                return f'moments/{video_filename}', None
        except Exception as thumb_error:
            print(f"缩略图生成失败: {thumb_error}")
            return f'moments/{video_filename}', None
            
    except Exception as e:
        raise Exception(f'视频保存失败：{str(e)}')
