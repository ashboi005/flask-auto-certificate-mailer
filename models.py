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
    resubmission_form_link = db.Column(db.String(255))  # Link for resubmission form
    feedback_form_link = db.Column(db.String(255))  # Link for feedback form

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
    
    # Project completion tracking
    completion_remarks = db.Column(db.Text)  # Remarks about project completion
    uncompletion_email_sent = db.Column(db.Boolean, default=False)  # Track if uncompletion email sent
    uncompletion_email_sent_at = db.Column(db.DateTime)  # When uncompletion email was sent
    
    # Certificate tracking
    certificate_sent = db.Column(db.Boolean, default=False)
    certificate_template_id = db.Column(db.Integer, db.ForeignKey('certificate_template.id'))
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EmailTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Template name (e.g., "Interview Invitation")
    subject = db.Column(db.String(255), nullable=False)  # Email subject with variables
    body = db.Column(db.Text, nullable=False)  # Email body with Jinja2-like variables
    description = db.Column(db.Text)  # Description of when to use this template
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Variables used in this template (stored as JSON string)
    template_variables = db.Column(db.Text)  # JSON: ["name", "meet_link", "time_slot", "custom_field"]
    
    # Static variables with predefined values (stored as JSON)
    static_variables = db.Column(db.Text)  # JSON: {"company_name": "TechCorp Inc.", "meet_link": "https://meet.google.com/xyz"}
    
    # Relationship
    user = db.relationship('User', backref='email_templates')

class MeetLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Display name (e.g., "Interview Room 1")
    url = db.Column(db.String(500), nullable=False)  # The actual Google Meet/Zoom link
    description = db.Column(db.Text)  # Optional description
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # To disable links without deleting
    
    # Relationship
    user = db.relationship('User', backref='meet_links')

class TemplateEmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('email_template.id'), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    subject_sent = db.Column(db.String(255), nullable=False)  # The actual subject sent (after variable replacement)
    body_sent = db.Column(db.Text, nullable=False)  # The actual body sent (after variable replacement)
    status = db.Column(db.String(20), default='sent')  # 'sent', 'failed', 'pending'
    error_message = db.Column(db.Text)  # If failed, store error message
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Variables used for this specific email (stored as JSON)
    variables_used = db.Column(db.Text)  # JSON of actual values used
    
    # Relationships
    template = db.relationship('EmailTemplate', backref='email_logs')
    user = db.relationship('User', backref='template_email_logs')
