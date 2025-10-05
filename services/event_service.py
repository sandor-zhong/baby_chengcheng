"""
事件服务
"""
from typing import List, Optional
from datetime import datetime, timedelta
from models import db, Event, User
from utils.time_utils import beijing_now
from sqlalchemy import func


class EventService:
    """事件服务类"""
    
    @staticmethod
    def create_event(user_id: int, event_type: str, amount_ml: Optional[int] = None, 
                    note: str = '') -> Event:
        """创建事件记录"""
        event = Event(
            user_id=user_id,
            type=event_type,
            amount_ml=amount_ml,
            note=note,
            timestamp=beijing_now()
        )
        db.session.add(event)
        db.session.commit()
        return event
    
    @staticmethod
    def get_user_events(user_id: int, event_type: Optional[str] = None, 
                       limit: int = 200) -> List[Event]:
        """获取用户事件列表"""
        query = Event.query.filter(Event.user_id == user_id)
        if event_type:
            query = query.filter(Event.type == event_type)
        return query.order_by(Event.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_last_event(user_id: int, event_type: str) -> Optional[Event]:
        """获取用户最后一次指定类型的事件"""
        return Event.query.filter(
            Event.user_id == user_id,
            Event.type == event_type
        ).order_by(Event.timestamp.desc()).first()
    
    @staticmethod
    def get_today_stats(user_id: int) -> dict:
        """获取今日统计"""
        now = beijing_now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        base_filters = [
            Event.user_id == user_id,
            Event.timestamp >= start_of_day
        ]
        
        today_feed_total_ml = db.session.query(
            func.coalesce(func.sum(Event.amount_ml), 0)
        ).filter(
            Event.type == 'feed', *base_filters
        ).scalar() or 0
        
        today_feed_count = db.session.query(func.count(Event.id)).filter(
            Event.type == 'feed', *base_filters
        ).scalar() or 0
        
        today_diaper_count = db.session.query(func.count(Event.id)).filter(
            Event.type == 'diaper', *base_filters
        ).scalar() or 0
        
        return {
            'today_feed_total_ml': int(today_feed_total_ml),
            'today_feed_count': int(today_feed_count),
            'today_diaper_count': int(today_diaper_count)
        }
    
    @staticmethod
    def delete_event(event_id: int, user_id: int) -> bool:
        """删除事件（验证权限）"""
        event = Event.query.filter(
            Event.id == event_id,
            Event.user_id == user_id
        ).first()
        
        if not event:
            return False
        
        db.session.delete(event)
        db.session.commit()
        return True
