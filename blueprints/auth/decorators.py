from functools import wraps
from flask import session, flash, redirect, url_for, current_app
from flask_jwt_extended import decode_token
from models import User
import traceback

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('token')
        if not token:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))        
        try:
            # Decode token using Flask-JWT-Extended
            decoded_token = decode_token(token)
            user_id = int(decoded_token['sub'])  # Convert string back to int
            current_user = User.query.get(user_id)
            if not current_user:
                flash('Invalid session. Please log in again.', 'error')
                return redirect(url_for('auth.login'))
        except Exception as e:
            # Debug: print the actual error
            print(f"JWT Decode Error: {e}")
            print(f"Token: {token}")
            traceback.print_exc()
            flash('Your session has expired. Please log in again.', 'error')
            return redirect(url_for('auth.login'))
        return f(current_user, *args, **kwargs)
    return decorated_function
