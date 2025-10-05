"""
装饰器模块
"""
import hashlib
import time
from functools import wraps
from flask import session, flash, redirect, url_for, request, jsonify


def login_required(view_func):
    """登录验证装饰器"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('uid'):
            flash('请先登录', 'warning')
            next_url = request.url
            return redirect(url_for('auth.login_page', next=next_url))
        return view_func(*args, **kwargs)
    return wrapper


def premium_required(view_func):
    """会员验证装饰器"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('uid'):
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login_page'))
        
        from models import User
        user = User.query.get(session.get('uid'))
        if not user or not user.is_premium():
            flash('此功能需要会员权限', 'warning')
            return redirect(url_for('membership.plans'))
        
        return view_func(*args, **kwargs)
    return wrapper


def cache_response(timeout: int = 300):
    """缓存响应装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键
            cache_key = hashlib.md5(f"{f.__name__}{args}{kwargs}".encode()).hexdigest()
            
            # 检查缓存
            if hasattr(cache_response, 'cache'):
                if cache_key in cache_response.cache:
                    cached_data, timestamp = cache_response.cache[cache_key]
                    if time.time() - timestamp < timeout:
                        return cached_data
            
            # 执行函数
            result = f(*args, **kwargs)
            
            # 存储到缓存
            if not hasattr(cache_response, 'cache'):
                cache_response.cache = {}
            cache_response.cache[cache_key] = (result, time.time())
            
            return result
        return decorated_function
    return decorator


def json_response(view_func):
    """JSON响应装饰器"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        try:
            result = view_func(*args, **kwargs)
            if isinstance(result, dict):
                return jsonify(result)
            return result
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return wrapper
