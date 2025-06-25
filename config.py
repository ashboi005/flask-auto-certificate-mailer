from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()

def configure_app(app: Flask):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///db.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']  
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  
    
    db.init_app(app)
    jwt.init_app(app)

