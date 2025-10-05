"""
认证蓝图：注册 / 登录 / 退出
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

SESSION_USER_ID = 'uid'

@auth_bp.get('/login')
def login_page():
	return render_template('login.html')

@auth_bp.post('/login')
def login_submit():
	email = (request.form.get('email') or '').strip().lower()
	password = request.form.get('password') or ''
	if not email or not password:
		flash('请输入邮箱和密码', 'warning')
		return redirect(url_for('auth.login_page'))
	user = User.query.filter_by(email=email).first()
	if not user or not check_password_hash(user.password_hash, password):
		flash('邮箱或密码错误', 'danger')
		return redirect(url_for('auth.login_page'))
	# 登录
	session[SESSION_USER_ID] = user.id
	flash('登录成功', 'success')
	return redirect(url_for('main.index'))

@auth_bp.get('/register')
def register_page():
	return render_template('register.html')

@auth_bp.post('/register')
def register_submit():
	email = (request.form.get('email') or '').strip().lower()
	password = request.form.get('password') or ''
	password2 = request.form.get('password2') or ''
	if not email or not password:
		flash('请输入邮箱和密码', 'warning')
		return redirect(url_for('auth.register_page'))
	if password != password2:
		flash('两次输入的密码不一致', 'warning')
		return redirect(url_for('auth.register_page'))
	# 唯一性校验
	if User.query.filter_by(email=email).first():
		flash('该邮箱已注册', 'warning')
		return redirect(url_for('auth.login_page'))
	# 创建
	u = User(email=email, password_hash=generate_password_hash(password))
	db.session.add(u)
	db.session.commit()
	flash('注册成功，请登录', 'success')
	return redirect(url_for('auth.login_page'))

@auth_bp.post('/logout')
def logout_submit():
	session.pop(SESSION_USER_ID, None)
	flash('您已退出登录', 'info')
	return redirect(url_for('main.index'))
