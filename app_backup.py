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

def is_parenting_related(title, description, content):
    """判断内容是否与育儿相关"""
    # 育儿相关关键词
    parenting_keywords = [
        '育儿', '宝宝', '婴儿', '幼儿', '儿童', '孩子', '亲子', '母婴', '怀孕', '孕期', '分娩', '母乳', '奶粉',
        '辅食', '睡眠', '哭闹', '发育', '成长', '教育', '早教', '幼儿园', '小学', '学习', '游戏', '玩具',
        '安全', '健康', '疫苗', '发烧', '感冒', '腹泻', '便秘', '湿疹', '过敏', '营养', '补钙', '维生素',
        'parenting', 'baby', 'infant', 'toddler', 'child', 'children', 'pregnancy', 'pregnant', 'breastfeeding',
        'formula', 'sleep', 'development', 'education', 'safety', 'health', 'vaccine', 'nutrition'
    ]
    
    # 非育儿相关关键词（需要过滤掉的内容）
    non_parenting_keywords = [
        '政治', '经济', '股票', '房价', '投资', '理财', '汽车', '房产', '旅游', '娱乐', '明星', '八卦',
        '体育', '足球', '篮球', '电竞', '游戏', '科技', '手机', '电脑', '互联网', '创业', '职场',
        'politics', 'economy', 'stock', 'investment', 'car', 'real estate', 'travel', 'entertainment',
        'celebrity', 'sports', 'football', 'basketball', 'technology', 'mobile', 'computer', 'internet'
    ]
    
    # 合并所有文本内容
    all_text = f"{title} {description} {content}".lower()
    
    # 检查是否包含非育儿关键词
    for keyword in non_parenting_keywords:
        if keyword.lower() in all_text:
            return False
    
    # 检查是否包含育儿关键词
    for keyword in parenting_keywords:
        if keyword.lower() in all_text:
            return True
    
    return False

def categorize_content(title, description, content):
    """智能分类内容"""
    all_text = f"{title} {description} {content}".lower()
    
    # 喂养相关关键词
    feeding_keywords = ['喂养', '母乳', '奶粉', '辅食', '吃饭', '营养', '补钙', '维生素', 'feeding', 'breastfeeding', 'formula', 'nutrition']
    
    # 健康相关关键词
    health_keywords = ['健康', '疫苗', '发烧', '感冒', '腹泻', '便秘', '湿疹', '过敏', '安全', 'health', 'vaccine', 'fever', 'cold', 'safety']
    
    # 发育相关关键词
    development_keywords = ['发育', '成长', '教育', '早教', '学习', '游戏', '玩具', 'development', 'education', 'learning', 'play', 'toy']
    
    # 睡眠相关关键词
    sleep_keywords = ['睡眠', '睡觉', '哭闹', '安抚', 'sleep', 'crying', 'comfort']
    
    # 检查关键词匹配
    if any(keyword in all_text for keyword in feeding_keywords):
        return 'feeding'
    elif any(keyword in all_text for keyword in health_keywords):
        return 'health'
    elif any(keyword in all_text for keyword in development_keywords):
        return 'development'
    elif any(keyword in all_text for keyword in sleep_keywords):
        return 'sleep'
    else:
        return 'parenting'  # 默认分类

def fetch_rss_content(feed_url):
    """抓取RSS内容"""
    try:
        print(f"开始抓取RSS: {feed_url}")
        
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        }
        
        # 先测试URL可访问性
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)
            print(f"HTTP状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"RSS源不可访问，状态码: {response.status_code}")
                return [], None
                
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return [], None
        
        # 解析RSS feed
        feed = feedparser.parse(feed_url)
        
        print(f"RSS解析状态: bozo={feed.bozo}, status={getattr(feed, 'status', 'unknown')}")
        
        if feed.bozo:
            print(f"RSS解析警告: {feed.bozo_exception}")
        
        # 检查是否有内容
        if not feed.entries:
            print("RSS源没有找到任何条目")
            return [], None
        
        print(f"找到 {len(feed.entries)} 个条目")
        
        items = []
        filtered_count = 0
        
        for i, entry in enumerate(feed.entries[:20]):  # 增加条目数量以便过滤
            try:
                title = entry.get('title', '无标题')
                description = entry.get('description', '')
                content = entry.get('content', [{}])[0].get('value', '') if hasattr(entry, 'content') else ''
                
                # 过滤非育儿相关内容
                if not is_parenting_related(title, description, content):
                    filtered_count += 1
                    print(f"过滤非育儿内容: {title[:50]}...")
                    continue
                
                # 智能分类
                auto_category = categorize_content(title, description, content)
                
                # 处理发布时间
                pub_date = beijing_now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=BEIJING_TZ)
                    except Exception as date_error:
                        print(f"日期解析错误: {date_error}")
                
                # 处理图片链接
                image_url = None
                if hasattr(entry, 'enclosures'):
                    for enclosure in entry.enclosures:
                        if enclosure.get('type', '').startswith('image/'):
                            image_url = enclosure.get('href')
                            break
                
                # 如果没有找到图片，尝试从内容中提取
                if not image_url and hasattr(entry, 'content'):
                    import re
                    img_match = re.search(r'<img[^>]+src="([^"]+)"', str(entry.content))
                    if img_match:
                        image_url = img_match.group(1)
                
                item = {
                    'title': title,
                    'description': description,
                    'content': content,
                    'link': entry.get('link', ''),
                    'image_url': image_url,
                    'pub_date': pub_date,
                    'auto_category': auto_category
                }
                items.append(item)
                print(f"处理条目 {i+1}: {title[:50]}... (分类: {auto_category})")
                
                # 只保留前10个育儿相关内容
                if len(items) >= 10:
                    break
                
            except Exception as entry_error:
                print(f"处理条目 {i+1} 时出错: {entry_error}")
                continue
        
        print(f"成功处理 {len(items)} 个育儿相关条目，过滤了 {filtered_count} 个非育儿内容")
        return items, feed.feed.get('title', '未知来源')
    
    except Exception as e:
        print(f"RSS抓取错误: {e}")
        import traceback
        traceback.print_exc()
        return [], None

def update_rss_feed(feed_id):
    """更新指定RSS源的内容"""
    try:
        print(f"开始更新RSS源 ID: {feed_id}")
        
        feed = RSSFeed.query.get(feed_id)
        if not feed:
            print(f"RSS源不存在: {feed_id}")
            return False
            
        if not feed.is_active:
            print(f"RSS源已停用: {feed.name}")
            return False
        
        print(f"正在更新RSS源: {feed.name} ({feed.url})")
        
        items, feed_title = fetch_rss_content(feed.url)
        if not items:
            print("没有获取到任何内容")
            return False
        
        print(f"获取到 {len(items)} 个新条目")
        
        # 更新feed标题（如果获取到了）
        if feed_title and feed_title != '未知来源':
            print(f"更新feed标题: {feed_title}")
            feed.name = feed_title
        
        # 添加新内容
        new_count = 0
        for item_data in items:
            # 检查是否已存在相同链接的内容
            existing_item = RSSItem.query.filter_by(
                feed_id=feed_id, 
                link=item_data['link']
            ).first()
            
            if not existing_item:
                # 使用智能分类结果
                auto_category = item_data.get('auto_category', 'parenting')
                
                new_item = RSSItem(
                    feed_id=feed_id,
                    title=item_data['title'],
                    description=item_data['description'],
                    content=item_data['content'],
                    link=item_data['link'],
                    image_url=item_data['image_url'],
                    pub_date=item_data['pub_date']
                )
                db.session.add(new_item)
                new_count += 1
                print(f"添加新条目: {item_data['title'][:50]}... (智能分类: {auto_category})")
            else:
                print(f"条目已存在，跳过: {item_data['title'][:50]}...")
        
        # 更新最后抓取时间
        feed.last_updated = beijing_now()
        db.session.commit()
        
        print(f"RSS源更新完成，新增 {new_count} 个条目")
        return True
    
    except Exception as e:
        print(f"更新RSS源错误: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return False


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

    # RSS订阅功能路由
    @app.route('/rss')
    def rss_feeds():
        """RSS订阅页面"""
        feeds = RSSFeed.query.filter_by(is_active=True).order_by(RSSFeed.name).all()
        return render_template('rss_feeds.html', feeds=feeds)
    
    @app.route('/rss/items')
    def rss_items():
        """RSS内容列表"""
        category = request.args.get('category', '')
        feed_id = request.args.get('feed_id', '')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        query = RSSItem.query.join(RSSFeed)
        
        if category:
            query = query.filter(RSSFeed.category == category)
        if feed_id:
            query = query.filter(RSSItem.feed_id == feed_id)
            
        items = query.order_by(RSSItem.pub_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('rss_items.html', items=items, category=category, feed_id=feed_id)
    
    @app.route('/rss/item/<int:item_id>')
    def rss_item_detail(item_id):
        """RSS内容详情"""
        item = RSSItem.query.get_or_404(item_id)
        # 标记为已读
        item.is_read = True
        db.session.commit()
        return render_template('rss_item_detail.html', item=item)
    
    @app.route('/api/rss/feeds', methods=['GET', 'POST'])
    def api_rss_feeds():
        """API: RSS源管理"""
        if request.method == 'GET':
            feeds = RSSFeed.query.filter_by(is_active=True).all()
            return jsonify([feed.to_dict() for feed in feeds])
        
        elif request.method == 'POST':
            data = request.get_json()
            feed = RSSFeed(
                name=data.get('name'),
                url=data.get('url'),
                description=data.get('description'),
                category=data.get('category'),
                icon_url=data.get('icon_url')
            )
            db.session.add(feed)
            db.session.commit()
            
            # 添加成功后立即抓取内容
            try:
                update_rss_feed(feed.id)
            except Exception as e:
                print(f"自动抓取RSS内容失败: {e}")
            
            return jsonify({'success': True, 'feed': feed.to_dict()})
    
    @app.route('/api/rss/items')
    def api_rss_items():
        """API: 获取RSS内容"""
        category = request.args.get('category', '')
        feed_id = request.args.get('feed_id', '')
        limit = int(request.args.get('limit', 20))
        
        query = RSSItem.query.join(RSSFeed)
        
        if category:
            query = query.filter(RSSFeed.category == category)
        if feed_id:
            query = query.filter(RSSItem.feed_id == feed_id)
            
        items = query.order_by(RSSItem.pub_date.desc()).limit(limit).all()
        return jsonify([item.to_dict() for item in items])
    
    @app.route('/api/rss/item/<int:item_id>/favorite', methods=['POST'])
    def api_rss_item_favorite(item_id):
        """API: 收藏/取消收藏RSS内容"""
        item = RSSItem.query.get_or_404(item_id)
        item.is_favorite = not item.is_favorite
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': item.is_favorite})
    
    @app.route('/api/rss/item/<int:item_id>/read', methods=['POST'])
    def api_rss_item_read(item_id):
        """API: 标记RSS内容为已读"""
        item = RSSItem.query.get_or_404(item_id)
        item.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    
    @app.route('/api/rss/feeds/<int:feed_id>/refresh', methods=['POST'])
    def api_refresh_rss_feed(feed_id):
        """手动刷新RSS源内容"""
        try:
            success = update_rss_feed(feed_id)
            if success:
                return jsonify({'success': True, 'message': 'RSS内容更新成功'})
            else:
                return jsonify({'success': False, 'message': 'RSS内容更新失败'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})
    
    @app.route('/api/rss/feeds/<int:feed_id>', methods=['PUT', 'DELETE'])
    def api_manage_rss_feed(feed_id):
        """管理RSS源：编辑或删除"""
        try:
            feed = RSSFeed.query.get_or_404(feed_id)
            
            if request.method == 'PUT':
                # 编辑RSS源
                data = request.get_json()
                feed.name = data.get('name', feed.name)
                feed.url = data.get('url', feed.url)
                feed.description = data.get('description', feed.description)
                feed.category = data.get('category', feed.category)
                feed.icon_url = data.get('icon_url', feed.icon_url)
                feed.is_active = data.get('is_active', feed.is_active)
                
                db.session.commit()
                return jsonify({'success': True, 'message': 'RSS源更新成功', 'feed': feed.to_dict()})
            
            elif request.method == 'DELETE':
                # 删除RSS源及其所有内容
                # 先删除相关的RSS内容
                RSSItem.query.filter_by(feed_id=feed_id).delete()
                # 再删除RSS源
                db.session.delete(feed)
                db.session.commit()
                return jsonify({'success': True, 'message': 'RSS源删除成功'})
                
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
    
    @app.route('/api/rss/feeds/<int:feed_id>/toggle', methods=['POST'])
    def api_toggle_rss_feed(feed_id):
        """切换RSS源启用/停用状态"""
        try:
            feed = RSSFeed.query.get_or_404(feed_id)
            feed.is_active = not feed.is_active
            db.session.commit()
            
            status = '启用' if feed.is_active else '停用'
            return jsonify({'success': True, 'message': f'RSS源已{status}', 'is_active': feed.is_active})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 9000)), debug=True)