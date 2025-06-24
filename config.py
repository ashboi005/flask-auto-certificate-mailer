from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()  # init db instance

def configure_app(app: Flask):  # configures entire flask app
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'  # link db
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.urandom(24)
    
    db.init_app(app)  # link db instance to app instance

