from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config import db
from models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('auth/signup.html')
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Validation
    if not username or not email or not password:
        flash('All fields are required.', 'error')
        return render_template('auth/signup.html')
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return render_template('auth/signup.html')
    
    if User.query.filter_by(email=email).first():
        flash('Email already registered.', 'error')
        return render_template('auth/signup.html')
    
    # Create new user
    password_hash = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=password_hash)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    except Exception as e:
        db.session.rollback()
        flash('Registration failed. Please try again.', 'error')
        return render_template('auth/signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Username and password are required.', 'error')
        return render_template('auth/login.html')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        token = create_access_token(identity=str(user.id))  
        session['token'] = token
        session['user_id'] = user.id
        flash('Login successful!', 'success')
        return redirect(url_for('main.dashboard'))
    
    
    flash('Invalid username or password.', 'error')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
