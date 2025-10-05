"""
用户服务
"""
from typing import Optional
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash


class UserService:
    """用户服务类"""
    
    @staticmethod
    def create_user(email: str, password: str) -> User:
        """创建用户"""
        if User.query.filter_by(email=email).first():
            raise ValueError('该邮箱已被注册')
        
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[User]:
        """验证用户登录"""
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            return user
        return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return User.query.get(user_id)
    
    @staticmethod
    def update_user_password(user_id: int, new_password: str) -> bool:
        """更新用户密码"""
        user = User.query.get(user_id)
        if not user:
            return False
        
        user.set_password(new_password)
        db.session.commit()
        return True
