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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/baby.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)
migrate = Migrate(app, db)

# 创建数据库表
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """首页"""
    # 获取最近的事件
    recent_events = Event.query.order_by(Event.timestamp.desc()).limit(5).all()
    
    # 获取今天的喂奶总量
    today = date.today()
    today_feedings = Event.query.filter(
        Event.type == 'feed',
        func.date(Event.timestamp) == today
    ).all()
    today_total_ml = sum(event.amount_ml for event in today_feedings if event.amount_ml)
    
    # 获取最近的照片
    recent_moments = Moment.query.filter(Moment.image_path.isnot(None)).order_by(Moment.timestamp.desc()).limit(3).all()
    
    return render_template('index.html', 
                         recent_events=recent_events,
                         today_total_ml=today_total_ml,
                         recent_moments=recent_moments)

@app.route('/events')
def events():
    """事件列表"""
    page = request.args.get('page', 1, type=int)
    events = Event.query.order_by(Event.timestamp.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('history.html', events=events)

@app.route('/moments')
def moments():
    """时光列表"""
    page = request.args.get('page', 1, type=int)
    show_favorites = request.args.get('favorites', 'false').lower() == 'true'
    
    query = Moment.query
    if show_favorites:
        query = query.filter(Moment.is_favorite == True)
    
    moments = query.order_by(Moment.timestamp.desc()).paginate(
        page=page, per_page=12, error_out=False)
    
    return render_template('moments.html', moments=moments, show_favorites=show_favorites)

@app.route('/create_moment')
def create_moment():
    """创建时光页面"""
    return render_template('create_moment.html')

@app.route('/settings')
def settings():
    """设置页面"""
    return render_template('settings.html')

@app.route('/api/events', methods=['POST'])
def add_event():
    """添加事件"""
    data = request.get_json()
    
    event = Event(
        type=data['type'],
        amount_ml=data.get('amount_ml'),
        note=data.get('note', '')
    )
    
    db.session.add(event)
    db.session.commit()
    
    return jsonify({'success': True, 'event': event.to_dict()})

@app.route('/api/moments', methods=['POST'])
def add_moment():
    """添加时光"""
    data = request.get_json()
    
    moment = Moment(
        content=data['content'],
        image_path=data.get('image_path'),
        thumb_path=data.get('thumb_path'),
        video_path=data.get('video_path')
    )
    
    db.session.add(moment)
    db.session.commit()
    
    return jsonify({'success': True, 'moment': moment.to_dict()})

@app.route('/api/moments/<int:moment_id>/favorite', methods=['POST'])
def toggle_favorite(moment_id):
    """切换收藏状态"""
    moment = Moment.query.get_or_404(moment_id)
    moment.is_favorite = not moment.is_favorite
    db.session.commit()
    
    return jsonify({'success': True, 'is_favorite': moment.is_favorite})

@app.route('/api/moments/<int:moment_id>', methods=['DELETE'])
def delete_moment(moment_id):
    """删除时光"""
    moment = Moment.query.get_or_404(moment_id)
    
    # 删除相关文件
    if moment.image_path and os.path.exists(moment.image_path):
        os.remove(moment.image_path)
    if moment.thumb_path and os.path.exists(moment.thumb_path):
        os.remove(moment.thumb_path)
    if moment.video_path and os.path.exists(moment.video_path):
        os.remove(moment.video_path)
    
    db.session.delete(moment)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/moment/<int:moment_id>')
def moment_detail(moment_id):
    """时光详情"""
    moment = Moment.query.get_or_404(moment_id)
    return render_template('moment_detail.html', moment=moment)

@app.route('/edit_moment/<int:moment_id>')
def edit_moment(moment_id):
    """编辑时光"""
    moment = Moment.query.get_or_404(moment_id)
    return render_template('edit_moment.html', moment=moment)

@app.route('/api/moments/<int:moment_id>', methods=['PUT'])
def update_moment(moment_id):
    """更新时光"""
    moment = Moment.query.get_or_404(moment_id)
    data = request.get_json()
    
    moment.content = data['content']
    if 'image_path' in data:
        moment.image_path = data['image_path']
    if 'thumb_path' in data:
        moment.thumb_path = data['thumb_path']
    if 'video_path' in data:
        moment.video_path = data['video_path']
    
    db.session.commit()
    
    return jsonify({'success': True, 'moment': moment.to_dict()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9000)
