import os
from datetime import datetime, timedelta, timezone, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, request as flask_request, session
from models import db, Event, Moment
from sqlalchemy import func
from flask_migrate import Migrate

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)


def create_app() -> Flask:
    app = Flask(__name__)

    # 基础配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'sqlite:///baby.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_UPLOAD_MB', '15')) * 1024 * 1024
    # 静态资源长缓存
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=30)

    # 数据库初始化
    db.init_app(app)

    migrate = Migrate(app, db)

    with app.app_context():
        db.create_all()
        # 创建加速查询的索引（若不存在）
        try:
            db.session.execute(
                db.text('CREATE INDEX IF NOT EXISTS idx_event_type_timestamp ON event (type, timestamp DESC)')
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

    # 工具函数
    def get_last_event(event_type: str):
        return Event.query.filter_by(type=event_type).order_by(Event.timestamp.desc()).first()

    def format_elapsed(delta: timedelta) -> str:
        total_minutes = int(delta.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def build_index_context():
        now = beijing_now()
        last_feed = get_last_event('feed')
        last_diaper = get_last_event('diaper')

        last_feed_time = last_feed.timestamp.strftime('%Y-%m-%d %H:%M:%S') if last_feed else None
        last_diaper_time = last_diaper.timestamp.strftime('%Y-%m-%d %H:%M:%S') if last_diaper else None
        # 直接使用北京时间，前端JavaScript会正确处理
        last_feed_ts = last_feed.timestamp.isoformat() if last_feed else None
        last_diaper_ts = last_diaper.timestamp.isoformat() if last_diaper else None

        # 确保数据库中的时间有时区信息
        if last_feed and last_feed.timestamp.tzinfo is None:
            last_feed.timestamp = last_feed.timestamp.replace(tzinfo=BEIJING_TZ)
        if last_diaper and last_diaper.timestamp.tzinfo is None:
            last_diaper.timestamp = last_diaper.timestamp.replace(tzinfo=BEIJING_TZ)
            
        feed_elapsed = format_elapsed(now - last_feed.timestamp) if last_feed else None
        diaper_elapsed = format_elapsed(now - last_diaper.timestamp) if last_diaper else None

        # 今日统计（UTC 天起算）
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_feed_total_ml = db.session.query(func.coalesce(func.sum(Event.amount_ml), 0)).filter(
            Event.type == 'feed', Event.timestamp >= start_of_day
        ).scalar() or 0
        today_feed_count = db.session.query(func.count(Event.id)).filter(
            Event.type == 'feed', Event.timestamp >= start_of_day
        ).scalar() or 0
        
        # 今日换尿布统计
        today_diaper_count = db.session.query(func.count(Event.id)).filter(
            Event.type == 'diaper', Event.timestamp >= start_of_day
        ).scalar() or 0

        return {
            'last_feed_time': last_feed_time,
            'last_diaper_time': last_diaper_time,
            'feed_elapsed': feed_elapsed,
            'diaper_elapsed': diaper_elapsed,
            'last_feed_ts': last_feed_ts,
            'last_diaper_ts': last_diaper_ts,
            'today_feed_total_ml': int(today_feed_total_ml),
            'today_feed_count': int(today_feed_count),
            'today_diaper_count': int(today_diaper_count),
        }

    # 压缩响应（gzip/br）
    try:
        from flask_compress import Compress
        Compress(app)
    except Exception:
        pass

    # 全局响应头：为静态资源设置缓存，为页面禁用缓存
    @app.after_request
    def add_cache_headers(response):
        path = flask_request.path
        if path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
        else:
            response.headers['Cache-Control'] = 'no-store'
        return response

    # 全局模板上下文：头像地址
    @app.context_processor
    def inject_avatar_url():
        # 优先使用环境变量 AVATAR_URL（可为绝对 URL）
        env_url = os.environ.get('AVATAR_URL')
        if env_url:
            return {'avatar_url': env_url}
        # 其次检测 static 下是否有用户自定义头像
        static_dir = app.static_folder or 'static'
        for fname in ['avatar.jpg', 'avatar.png', 'avatar.jpeg']:
            candidate = os.path.join(static_dir, fname)
            if os.path.exists(candidate):
                try:
                    v = int(os.path.getmtime(candidate))
                except Exception:
                    v = 0
                return {'avatar_url': url_for('static', filename=fname) + f'?v={v}'}
        # 默认占位图
        try:
            v = int(os.path.getmtime(os.path.join(static_dir, 'avatar-default.svg')))
        except Exception:
            v = 0
        return {'avatar_url': url_for('static', filename='avatar-default.svg') + f'?v={v}'}

    # 宝宝资料：读取/保存到 instance/profile.json
    def instance_file(pathname: str) -> str:
        inst = app.instance_path
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

    @app.context_processor
    def inject_profile():
        prof = load_profile()
        # 顶部背景（封面）图：与头像逻辑一致，支持覆盖与默认
        cover_env = os.environ.get('COVER_URL')
        cover_url = None
        if cover_env:
            cover_url = cover_env
        else:
            static_dir = app.static_folder or 'static'
            for fname in ['cover.jpg', 'cover.png', 'cover.jpeg']:
                candidate = os.path.join(static_dir, fname)
                if os.path.exists(candidate):
                    try:
                        v = int(os.path.getmtime(candidate))
                    except Exception:
                        v = 0
                    cover_url = url_for('static', filename=fname) + f'?v={v}'
                    break
        if not cover_url:
            try:
                v = int(os.path.getmtime(os.path.join(app.static_folder or 'static', 'cover-default.jpg')))
            except Exception:
                v = 0
            cover_url = url_for('static', filename='cover-default.jpg') + f'?v={v}'
        # 若存在压缩后的 cover.webp 优先使用
        try:
            v_webp = int(os.path.getmtime(os.path.join(app.static_folder or 'static', 'cover.webp')))
            cover_url = url_for('static', filename='cover.webp') + f'?v={v_webp}'
        except Exception:
            pass
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
                anchor = _add_months(b, age_months)
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

    @app.post('/profile')
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
                return redirect(request.referrer or url_for('index'))
        try:
            prof = load_profile()
            prof['name'] = name
            prof['birth'] = birth
            save_profile(prof)
            flash('宝宝资料已保存', 'success')
        except Exception as exc:
            flash('保存失败：' + str(exc), 'danger')
        return redirect(request.referrer or url_for('index'))

    @app.get('/settings')
    def settings():
        # 直接渲染，模板可使用注入的 baby_* 变量
        return render_template('settings.html')

    # 上传/更换头像
    @app.post('/avatar/upload')
    def upload_avatar():
        f = request.files.get('avatar')
        if not f or f.filename == '':
            flash('未选择图片', 'warning')
            return redirect(request.referrer or url_for('index'))
        # 校验扩展名
        filename = f.filename.lower()
        ext = None
        for e in ('jpg', 'jpeg', 'png'):
            if filename.endswith('.' + e):
                ext = e
                break
        if not ext:
            flash('仅支持 JPG/PNG 图片', 'warning')
            return redirect(request.referrer or url_for('index'))
        # 保存到 static 下的固定文件名
        target_name = 'avatar.jpg' if ext in ('jpg', 'jpeg') else 'avatar.png'
        try:
            save_path = os.path.join(app.static_folder or 'static', target_name)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            f.save(save_path)
            flash('头像已更新', 'success')
        except Exception as exc:
            flash('头像更新失败：' + str(exc), 'danger')
        return redirect(request.referrer or url_for('index'))

    @app.post('/cover/upload')
    def upload_cover():
        f = request.files.get('cover')
        if not f or f.filename == '':
            flash('未选择封面图片', 'warning')
            return redirect(request.referrer or url_for('index'))
        filename = f.filename.lower()
        ext = None
        for e in ('jpg', 'jpeg', 'png'):
            if filename.endswith('.' + e):
                ext = e
                break
        if not ext:
            flash('仅支持 JPG/PNG 图片', 'warning')
            return redirect(request.referrer or url_for('index'))
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
            out_path = os.path.join(app.static_folder or 'static', 'cover.webp')
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            img.save(out_path, format='WEBP', quality=int(os.environ.get('COVER_QUALITY', '85')))
            flash('封面已更新并压缩为 WebP', 'success')
        except Exception as exc:
            flash('封面更新失败：' + str(exc), 'danger')
        return redirect(request.referrer or url_for('index'))

    # 路由定义
    @app.route('/')
    def index():
        ctx = build_index_context()
        return render_template('index.html', **ctx)

    @app.route('/record_feed', methods=['POST'])
    def record_feed():
        try:
            amount = request.form.get('amount_ml')
            note = request.form.get('note', '')
            if not amount:
                flash('请填写奶量（ml）', 'warning')
                return redirect(url_for('index') + '#feed-pane')
            amount = int(amount)
            e = Event(type='feed', amount_ml=amount, note=note, timestamp=beijing_now())
            db.session.add(e)
            db.session.commit()
            flash(f'已记录喂奶 {amount} ml', 'success')
            session['undo_event_id'] = e.id
            session['undo_expire_ts'] = beijing_now().isoformat()
        except Exception as exc:
            flash('记录失败：' + str(exc), 'danger')
        return redirect(url_for('index') + '#feed-pane')

    @app.route('/record_diaper', methods=['POST'])
    def record_diaper():
        try:
            note = request.form.get('note', '')
            diaper_kind = request.form.get('diaper_kind', '')
            kind_label = {'pee': '尿', 'poop': '便', 'both': '尿+便'}.get(diaper_kind, '')
            if kind_label:
                note = f'[{kind_label}] ' + (note or '')
            e = Event(type='diaper', amount_ml=None, note=note, timestamp=beijing_now())
            db.session.add(e)
            db.session.commit()
            flash('已记录换尿布', 'success')
            session['undo_event_id'] = e.id
            session['undo_expire_ts'] = beijing_now().isoformat()
        except Exception as exc:
            flash('记录失败：' + str(exc), 'danger')
        return redirect(url_for('index') + '#diaper-pane')

    @app.route('/history')
    def history():
            t = request.args.get('type', 'all')
            q = Event.query
            if t == 'feed':
                q = q.filter_by(type='feed')
            elif t == 'diaper':
                q = q.filter_by(type='diaper')
            events = q.order_by(Event.timestamp.desc()).limit(200).all()
            return render_template('history.html', events=events, filter_type=t)

    @app.post('/event/<int:event_id>/delete')
    def delete_event(event_id: int):
        e = Event.query.get_or_404(event_id)
        try:
            db.session.delete(e)
            db.session.commit()
            flash('已删除记录', 'success')
        except Exception as exc:
            db.session.rollback()
            flash('删除失败：' + str(exc), 'danger')
        return redirect(request.referrer or url_for('history'))

    @app.post('/undo_last')
    def undo_last():
        undo_id = session.get('undo_event_id')
        undo_ts = session.get('undo_expire_ts')
        if not undo_id or not undo_ts:
            flash('没有可撤销的记录', 'warning')
            return redirect(url_for('index'))
        try:
            ts = datetime.fromisoformat(undo_ts)
            # 确保ts有时区信息，如果没有则添加北京时区
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=BEIJING_TZ)
            if beijing_now() - ts > timedelta(seconds=30):
                flash('撤销已超时', 'warning')
                session.pop('undo_event_id', None)
                session.pop('undo_expire_ts', None)
                return redirect(url_for('index'))
        except Exception:
            pass
        e = Event.query.get(undo_id)
        if not e:
            flash('记录不存在，无法撤销', 'warning')
        else:
            try:
                db.session.delete(e)
                db.session.commit()
                flash('已撤销刚才的记录', 'success')
            except Exception as exc:
                db.session.rollback()
                flash('撤销失败：' + str(exc), 'danger')
        session.pop('undo_event_id', None)
        session.pop('undo_expire_ts', None)
        return redirect(url_for('index'))

    @app.route('/api/last')
    def api_last():
        last_feed = get_last_event('feed')
        last_diaper = get_last_event('diaper')
        return jsonify({
            'last_feed': last_feed.to_dict() if last_feed else None,
            'last_diaper': last_diaper.to_dict() if last_diaper else None,
            'now': beijing_now().isoformat()
        })

    @app.route('/api/feed_series')
    def api_feed_series():
        try:
            limit = int(request.args.get('limit', 30))
            limit = max(1, min(limit, 200))
        except Exception:
            limit = 30
        events = (
            Event.query
            .filter_by(type='feed')
            .order_by(Event.timestamp.desc())
            .limit(limit)
            .all()
        )
        events = list(reversed(events))
        data = [
            {
                'ts': e.timestamp.isoformat(),
                'amount_ml': e.amount_ml or 0,
            }
            for e in events
        ]
        return jsonify({'items': data, 'count': len(data)})

    @app.route('/api/diaper_series')
    def api_diaper_series():
        try:
            days = int(request.args.get('days', 14))
            days = max(1, min(days, 60))
        except Exception:
            days = 14
        now = beijing_now()
        start = (now - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        events = (
            Event.query
            .filter(Event.type == 'diaper', Event.timestamp >= start)
            .order_by(Event.timestamp.asc())
            .all()
        )
        buckets = {}
        for i in range(days):
            day = (start + timedelta(days=i)).date().isoformat()
            buckets[day] = {'day': day, 'total': 0, 'pee': 0, 'poop': 0, 'both': 0}
        for e in events:
            day = e.timestamp.date().isoformat()
            b = buckets.get(day)
            if not b:
                continue
            b['total'] += 1
            note = (e.note or '')
            if note.startswith('[尿+便]'):
                b['both'] += 1
            elif note.startswith('[尿]'):
                b['pee'] += 1
            elif note.startswith('[便]'):
                b['poop'] += 1
        items = [buckets[(start + timedelta(days=i)).date().isoformat()] for i in range(days)]
        return jsonify({'items': items, 'count': len(items)})

    @app.route('/favicon.ico')
    def favicon():
        return ('', 204)

    @app.route('/api/server_time')
    def api_server_time():
        """获取服务器时间（北京时间）"""
        return jsonify({
            'server_time': beijing_now().isoformat()
        })

        # ===== 时光相关路由 =====
    @app.route('/moments')
    def moments():
        """时光页面 - 类似朋友圈"""
        page = request.args.get('page', 1, type=int)
        per_page = 10
        moments = Moment.query.order_by(Moment.timestamp.desc()).paginate(
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

        return render_template('moments.html', moments=moments, groups=groups)

    @app.route('/moments/create', methods=['GET', 'POST'])
    def create_moment():
        """发布时光"""
        if request.method == 'GET':
            return render_template('create_moment.html')

        try:
            content = request.form.get('content', '').strip()
            if not content:
                flash('请输入内容', 'warning')
                return redirect(url_for('create_moment'))

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
                            img_path = os.path.join(app.static_folder or 'static', image_path)
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

            moment = Moment(content=content, image_path=image_path, thumb_path=thumb_path, video_path=video_path)
            db.session.add(moment)
            db.session.commit()

            flash('发布成功！', 'success')
            return redirect(url_for('moments'))

        except Exception as e:
            flash(f'发布失败：{str(e)}', 'danger')
            return redirect(url_for('create_moment'))

    @app.route('/moments/<int:moment_id>/delete', methods=['POST'])
    def delete_moment(moment_id):
        """删除时光"""
        try:
            moment = Moment.query.get_or_404(moment_id)
            # 删除图片文件
            if moment.image_path and os.path.exists(moment.image_path):
                os.remove(moment.image_path)
            db.session.delete(moment)
            db.session.commit()
            flash('删除成功', 'success')
        except Exception as e:
            flash(f'删除失败：{str(e)}', 'danger')
        return redirect(url_for('moments'))

    @app.route('/moments/<int:moment_id>')
    def moment_detail(moment_id: int):
        """时光详情页（查看，不编辑）"""
        moment = Moment.query.get_or_404(moment_id)
        # 上下条（同页内）
        prev_m = (
            Moment.query.filter(Moment.timestamp > moment.timestamp)
            .order_by(Moment.timestamp.asc())
            .first()
        )
        next_m = (
            Moment.query.filter(Moment.timestamp < moment.timestamp)
            .order_by(Moment.timestamp.desc())
            .first()
        )
        return render_template('moment_detail.html', moment=moment, prev_m=prev_m, next_m=next_m)

    @app.route('/moments/<int:moment_id>/favorite', methods=['POST'])
    def toggle_favorite(moment_id: int):
        """切换收藏状态"""
        moment = Moment.query.get_or_404(moment_id)
        moment.is_favorite = not moment.is_favorite
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': moment.is_favorite})

    @app.route('/moments/<int:moment_id>/share')
    def share_moment(moment_id: int):
        """分享时光"""
        moment = Moment.query.get_or_404(moment_id)
        # 生成分享链接
        share_url = request.url_root + url_for('moment_detail', moment_id=moment_id)
        return jsonify({
            'success': True,
            'share_url': share_url,
            'title': f'宝宝时光 - {moment.timestamp.strftime("%Y-%m-%d %H:%M")}',
            'description': moment.content[:100] + '...' if len(moment.content) > 100 else moment.content
        })

    @app.route('/moments/<int:moment_id>/edit', methods=['GET', 'POST'])
    def edit_moment(moment_id):
        """编辑时光"""
        moment = Moment.query.get_or_404(moment_id)
        if request.method == 'GET':
            return render_template('edit_moment.html', moment=moment)
        try:
            content = request.form.get('content', '').strip()
            if not content:
                flash('内容不能为空', 'warning')
                return redirect(url_for('edit_moment', moment_id=moment_id))

            # 更新文字
            moment.content = content

            # 如上传新图则替换并删除旧图
            if 'image' in request.files:
                f = request.files['image']
                if f and f.filename:
                    new_path = save_moment_image(f)
                    # 删除旧文件
                    try:
                        if moment.image_path and os.path.exists(os.path.join(app.static_folder or 'static', moment.image_path)):
                            os.remove(os.path.join(app.static_folder or 'static', moment.image_path))
                    except Exception:
                        pass
                    moment.image_path = new_path
                    # 同步更新缩略图路径（若存在）
                    try:
                        base = os.path.basename(new_path) if new_path else None
                        if base and base.endswith('.webp'):
                            name = base[:-5]
                            thumb_candidate = os.path.join(app.static_folder or 'static', 'moments', name + '_thumb.webp')
                            if os.path.exists(thumb_candidate):
                                moment.thumb_path = 'moments/' + name + '_thumb.webp'
                    except Exception:
                        pass

            db.session.commit()
            flash('已保存修改', 'success')
            return redirect(url_for('moments'))
        except Exception as exc:
            db.session.rollback()
            flash('保存失败：' + str(exc), 'danger')
            return redirect(url_for('edit_moment', moment_id=moment_id))

    def save_moment_image(image_file):
        """保存并压缩时光图片"""
        try:
            from PIL import Image
            import io

            # 创建时光图片目录
            moments_dir = os.path.join(app.static_folder or 'static', 'moments')
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
                moments_dir = os.path.join(app.static_folder or 'static', 'moments')
                os.makedirs(moments_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                video_filename = f'moment_{timestamp}.mp4'
                video_filepath = os.path.join(moments_dir, video_filename)
                video_file.save(video_filepath)
                return f'moments/{video_filename}', None
            
            moments_dir = os.path.join(app.static_folder or 'static', 'moments')
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

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 9000)), debug=True)