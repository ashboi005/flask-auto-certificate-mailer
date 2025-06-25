from config import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    hackathons = db.relationship('Hackathon', backref='user', lazy=True)

class Hackathon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    certificate_templates = db.relationship('CertificateTemplate', backref='hackathon', lazy=True)
    participants = db.relationship('Participant', backref='hackathon', lazy=True)

class CertificateTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Winner", "Participation"
    filename = db.Column(db.String(255), nullable=False)
    name_x_position = db.Column(db.Float, default=300)
    name_y_position = db.Column(db.Float, default=400)
    font_size = db.Column(db.Integer, default=24)
    font_color = db.Column(db.String(7), default='#000000')
    hackathon_id = db.Column(db.Integer, db.ForeignKey('hackathon.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    hackathon_id = db.Column(db.Integer, db.ForeignKey('hackathon.id'), nullable=False)
    
    # Team information
    team_name = db.Column(db.String(100))  # Name of the team (if applicable)
    member_position = db.Column(db.Integer)  # 1st, 2nd, or 3rd member
    
    # Certificate tracking
    certificate_sent = db.Column(db.Boolean, default=False)
    certificate_template_id = db.Column(db.Integer, db.ForeignKey('certificate_template.id'))
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
