from flask import Blueprint, render_template, session, redirect, url_for
from blueprints.auth.decorators import login_required
from models import Hackathon, CertificateTemplate, Participant

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'token' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard(current_user):
    # Fetch user's hackathons
    hackathons = Hackathon.query.filter_by(user_id=current_user.id).order_by(Hackathon.created_at.desc()).all()
    
    # Calculate stats
    total_hackathons = len(hackathons)
    total_templates = CertificateTemplate.query.join(Hackathon).filter(Hackathon.user_id == current_user.id).count()
    total_participants = Participant.query.join(Hackathon).filter(Hackathon.user_id == current_user.id).count()
    certificates_sent = Participant.query.join(Hackathon).filter(
        Hackathon.user_id == current_user.id,
        Participant.certificate_sent == True
    ).count()
    
    # Get recent hackathons (latest 5)
    recent_hackathons = hackathons[:5]
    
    return render_template('main/dashboard.html', 
                         user=current_user,
                         total_hackathons=total_hackathons,
                         total_templates=total_templates,
                         total_participants=total_participants,
                         certificates_sent=certificates_sent,
                         recent_hackathons=recent_hackathons)
