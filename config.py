"""
应用配置管理
"""
import os
from datetime import timedelta
from typing import Optional


class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_MB', '15')) * 1024 * 1024
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(days=30)
    
    # AI配置
    AI_MODEL_TYPE = os.environ.get('AI_MODEL_TYPE', 'ollama')
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    AI_FAST_MODE = os.environ.get('AI_FAST_MODE', 'true').lower() == 'true'
    
    # 时区配置
    TIMEZONE_OFFSET = 8  # 北京时间 UTC+8


def _get_database_url() -> str:
    """获取数据库URL，处理不同平台的URL格式"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return 'sqlite:///baby.db'
    
    # 处理Render等平台的数据库URL
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///baby.db'


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _get_database_url()


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
