import os
from flask import Flask, request as flask_request, session, url_for
from flask_migrate import Migrate
from models import db, User
from config import config
from utils.time_utils import beijing_now

# 导入蓝图
from blueprints.main import main_bp
from blueprints.moments import moments_bp
from blueprints.ai import ai_bp
from blueprints.profile import profile_bp
from blueprints.auth import auth_bp



def create_app(config_name: str = None) -> Flask:
    """应用工厂函数"""
    app = Flask(__name__)

    # 配置
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])

    # 数据库初始化
    db.init_app(app)
    migrate = Migrate(app, db)

    # 初始化数据库
    with app.app_context():
        db.create_all()
        _create_indexes()

    # 注册中间件
    _register_middleware(app)
    
    # 注册上下文处理器
    _register_context_processors(app)
    
    # 注册蓝图
    _register_blueprints(app)

    return app


def _create_indexes():
    """创建数据库索引"""
    try:
        db.session.execute(
            db.text('CREATE INDEX IF NOT EXISTS idx_event_type_timestamp ON event (type, timestamp DESC)')
        )
        db.session.execute(
            db.text('CREATE INDEX IF NOT EXISTS idx_event_user_id ON event (user_id)')
        )
        db.session.execute(
            db.text('CREATE INDEX IF NOT EXISTS idx_moment_user_id ON moment (user_id)')
        )
        db.session.commit()
    except Exception:
        db.session.rollback()


def _register_middleware(app):
    """注册中间件"""
    # 压缩响应
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


def _register_context_processors(app):
    """注册上下文处理器"""
    @app.context_processor
    def inject_current_user():
        uid = session.get('uid')
        user = None
        if uid:
            try:
                user = User.query.get(uid)
            except Exception:
                user = None
        return {'current_user': user}

    @app.context_processor
    def inject_avatar_url():
        from utils.static_utils import get_avatar_url
        return {'avatar_url': get_avatar_url(app)}

    @app.context_processor
    def inject_profile():
        from utils.static_utils import get_profile_context
        return get_profile_context(app)


def _register_blueprints(app):
    """注册蓝图"""
    app.register_blueprint(main_bp)
    app.register_blueprint(moments_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(auth_bp)


app = create_app()

if __name__ == '__main__':
    # 生产环境使用gunicorn，开发环境使用Flask开发服务器
    port = int(os.environ.get('PORT', 9000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)