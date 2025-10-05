"""
主页和基础功能蓝图
包含：喂奶记录、换尿布记录、历史记录等核心功能
"""
import os
import json
from datetime import datetime, timedelta, timezone, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from models import db, Event
from flask import current_app
from sqlalchemy import func

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

# 创建蓝图
main_bp = Blueprint('main', __name__)

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
    # 按用户过滤 - 未登录不显示数据
    from flask import session
    uid = session.get('uid')
    if not uid:
        # 未登录时返回空数据
        return {
            'last_feed_time': None,
            'last_diaper_time': None,
            'feed_elapsed': None,
            'diaper_elapsed': None,
            'last_feed_ts': None,
            'last_diaper_ts': None,
            'today_feed_total_ml': 0,
            'today_feed_count': 0,
            'today_diaper_count': 0,
        }
    
    q = Event.query.filter(Event.user_id == uid)
    last_feed = q.filter_by(type='feed').order_by(Event.timestamp.desc()).first()
    last_diaper = q.filter_by(type='diaper').order_by(Event.timestamp.desc()).first()

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
    base_filters = [Event.timestamp >= start_of_day, Event.user_id == uid]
    today_feed_total_ml = db.session.query(func.coalesce(func.sum(Event.amount_ml), 0)).filter(
        Event.type == 'feed', *base_filters
    ).scalar() or 0
    today_feed_count = db.session.query(func.count(Event.id)).filter(
        Event.type == 'feed', *base_filters
    ).scalar() or 0
    
    # 今日换尿布统计
    today_diaper_count = db.session.query(func.count(Event.id)).filter(
        Event.type == 'diaper', *base_filters
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

@main_bp.route('/')
def index():
    ctx = build_index_context()
    return render_template('index.html', **ctx)

from utils.decorators import login_required

@main_bp.route('/record_feed', methods=['POST'])
@login_required
def record_feed():
    try:
        from flask import session
        uid = session.get('uid')
        amount = request.form.get('amount_ml')
        note = request.form.get('note', '')
        if not amount:
            flash('请填写奶量（ml）', 'warning')
            return redirect(url_for('main.index') + '#feed-pane')
        amount = int(amount)
        e = Event(type='feed', amount_ml=amount, note=note, timestamp=beijing_now(), user_id=uid)
        db.session.add(e)
        db.session.commit()
        flash(f'已记录喂奶 {amount} ml', 'success')
        session['undo_event_id'] = e.id
        session['undo_expire_ts'] = beijing_now().isoformat()
    except Exception as exc:
        flash('记录失败：' + str(exc), 'danger')
    return redirect(url_for('main.index') + '#feed-pane')

@main_bp.route('/record_diaper', methods=['POST'])
@login_required
def record_diaper():
    try:
        from flask import session
        uid = session.get('uid')
        note = request.form.get('note', '')
        diaper_kind = request.form.get('diaper_kind', '')
        kind_label = {'pee': '尿', 'poop': '便', 'both': '尿+便'}.get(diaper_kind, '')
        if kind_label:
            note = f'[{kind_label}] ' + (note or '')
        e = Event(type='diaper', amount_ml=None, note=note, timestamp=beijing_now(), user_id=uid)
        db.session.add(e)
        db.session.commit()
        flash('已记录换尿布', 'success')
        session['undo_event_id'] = e.id
        session['undo_expire_ts'] = beijing_now().isoformat()
    except Exception as exc:
        flash('记录失败：' + str(exc), 'danger')
    return redirect(url_for('main.index') + '#diaper-pane')

@main_bp.route('/history')
def history():
    t = request.args.get('type', 'all')
    from flask import session
    uid = session.get('uid')
    if not uid:
        # 未登录时返回空列表
        return render_template('history.html', events=[], filter_type=t)
    
    q = Event.query.filter(Event.user_id == uid)
    if t == 'feed':
        q = q.filter_by(type='feed')
    elif t == 'diaper':
        q = q.filter_by(type='diaper')
    events = q.order_by(Event.timestamp.desc()).limit(200).all()
    return render_template('history.html', events=events, filter_type=t)

@main_bp.post('/event/<int:event_id>/delete')
@login_required
def delete_event(event_id: int):
    from flask import session
    uid = session.get('uid')
    e = Event.query.get_or_404(event_id)
    if uid and e.user_id and e.user_id != uid:
        flash('无权限删除该记录', 'danger')
        return redirect(request.referrer or url_for('main.history'))
    try:
        db.session.delete(e)
        db.session.commit()
        flash('已删除记录', 'success')
    except Exception as exc:
        db.session.rollback()
        flash('删除失败：' + str(exc), 'danger')
    return redirect(request.referrer or url_for('main.history'))

@main_bp.post('/undo_last')
@login_required
def undo_last():
    undo_id = session.get('undo_event_id')
    undo_ts = session.get('undo_expire_ts')
    if not undo_id or not undo_ts:
        flash('没有可撤销的记录', 'warning')
        return redirect(url_for('main.index'))
    try:
        ts = datetime.fromisoformat(undo_ts)
        # 确保ts有时区信息，如果没有则添加北京时区
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=BEIJING_TZ)
        if beijing_now() - ts > timedelta(seconds=30):
            flash('撤销已超时', 'warning')
            session.pop('undo_event_id', None)
            session.pop('undo_expire_ts', None)
            return redirect(url_for('main.index'))
    except Exception:
        pass
    e = Event.query.get(undo_id)
    if not e:
        flash('记录不存在，无法撤销', 'warning')
    else:
        from flask import session
        uid = session.get('uid')
        if uid and e.user_id and e.user_id != uid:
            flash('无权限撤销该记录', 'danger')
            session.pop('undo_event_id', None)
            session.pop('undo_expire_ts', None)
            return redirect(url_for('main.index'))
        try:
            db.session.delete(e)
            db.session.commit()
            flash('已撤销刚才的记录', 'success')
        except Exception as exc:
            db.session.rollback()
            flash('撤销失败：' + str(exc), 'danger')
    session.pop('undo_event_id', None)
    session.pop('undo_expire_ts', None)
    return redirect(url_for('main.index'))

@main_bp.route('/api/last')
def api_last():
    from flask import session
    uid = session.get('uid')
    if not uid:
        return jsonify({
            'last_feed': None,
            'last_diaper': None,
            'now': beijing_now().isoformat()
        })
    
    last_feed = Event.query.filter(Event.user_id == uid, Event.type == 'feed').order_by(Event.timestamp.desc()).first()
    last_diaper = Event.query.filter(Event.user_id == uid, Event.type == 'diaper').order_by(Event.timestamp.desc()).first()
    return jsonify({
        'last_feed': last_feed.to_dict() if last_feed else None,
        'last_diaper': last_diaper.to_dict() if last_diaper else None,
        'now': beijing_now().isoformat()
    })

@main_bp.route('/api/feed_series')
def api_feed_series():
    from flask import session
    uid = session.get('uid')
    if not uid:
        return jsonify({'items': [], 'count': 0})
    
    try:
        limit = int(request.args.get('limit', 30))
        limit = max(1, min(limit, 200))
    except Exception:
        limit = 30
    events = (
        Event.query
        .filter(Event.user_id == uid, Event.type == 'feed')
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

@main_bp.route('/api/diaper_series')
def api_diaper_series():
    from flask import session
    uid = session.get('uid')
    if not uid:
        return jsonify({'items': [], 'count': 0})
    
    try:
        days = int(request.args.get('days', 14))
        days = max(1, min(days, 60))
    except Exception:
        days = 14
    now = beijing_now()
    start = (now - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
    events = (
        Event.query
        .filter(Event.user_id == uid, Event.type == 'diaper', Event.timestamp >= start)
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

@main_bp.route('/favicon.ico')
def favicon():
    return ('', 204)

@main_bp.route('/api/server_time')
def api_server_time():
    """获取服务器时间（北京时间）"""
    return jsonify({
        'server_time': beijing_now().isoformat()
    })
