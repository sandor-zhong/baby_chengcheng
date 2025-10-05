from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(120), unique=True, nullable=False, index=True)
	password_hash = db.Column(db.String(255), nullable=False)
	created_at = db.Column(db.DateTime, nullable=False, default=beijing_now, index=True)
	
	def set_password(self, password):
		"""设置密码"""
		self.password_hash = generate_password_hash(password)
	
	def check_password(self, password):
		"""验证密码"""
		return check_password_hash(self.password_hash, password)
	
	def __repr__(self):
		return f'<User {self.email}>'

class Event(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	type = db.Column(db.String(20), nullable=False, index=True)  # 'feed' 或 'diaper' - 添加索引
	amount_ml = db.Column(db.Integer, nullable=True)
	note = db.Column(db.Text, nullable=True, default='')
	timestamp = db.Column(db.DateTime, nullable=False, default=beijing_now, index=True)  # 添加索引
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

	# 添加复合索引
	__table_args__ = (
		db.Index('idx_event_type_timestamp', 'type', 'timestamp'),
	)

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
	is_favorite = db.Column(db.Boolean, default=False, index=True)  # 是否收藏 - 添加索引
	timestamp = db.Column(db.DateTime, nullable=False, default=beijing_now, index=True)  # 添加索引
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

	# 添加复合索引
	__table_args__ = (
		db.Index('idx_moment_timestamp_favorite', 'timestamp', 'is_favorite'),
		db.Index('idx_moment_content', 'content'),  # 为内容搜索添加索引
	)
	
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

# 已移除SMSReminder模型
