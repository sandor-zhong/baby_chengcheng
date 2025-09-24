from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta

db = SQLAlchemy()

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

class Event(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	type = db.Column(db.String(20), nullable=False)  # 'feed' 或 'diaper'
	amount_ml = db.Column(db.Integer, nullable=True)
	note = db.Column(db.Text, nullable=True, default='')
	timestamp = db.Column(db.DateTime, nullable=False, default=beijing_now)

	def to_dict(self):
		return {
			"id": self.id,
			"type": self.type,
			"amount_ml": self.amount_ml,
			"note": self.note,
			"timestamp": self.timestamp.isoformat()
		}

class Moment(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	content = db.Column(db.Text, nullable=False)  # 文字内容
	image_path = db.Column(db.String(255), nullable=True)  # 图片路径
	thumb_path = db.Column(db.String(255), nullable=True)  # 缩略图路径
	video_path = db.Column(db.String(255), nullable=True)  # 视频路径
	is_favorite = db.Column(db.Boolean, default=False)  # 是否收藏
	timestamp = db.Column(db.DateTime, nullable=False, default=beijing_now)
	
	def to_dict(self):
		return {
			"id": self.id,
			"content": self.content,
			"image_path": self.image_path,
			"thumb_path": self.thumb_path,
			"video_path": self.video_path,
			"is_favorite": self.is_favorite,
			"timestamp": self.timestamp.isoformat()
		}