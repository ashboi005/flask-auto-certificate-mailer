from flask import Blueprint, render_template, request, redirect, url_for, flash
from blueprints.auth.decorators import login_required
from config import db
from models import Hackathon

hackathon_bp = Blueprint('hackathon', __name__)

@hackathon_bp.route('/hackathons')
@login_required
def list_hackathons(current_user):
    hackathons = Hackathon.query.filter_by(user_id=current_user.id).order_by(Hackathon.created_at.desc()).all()
    return render_template('hackathon/list.html', hackathons=hackathons, user=current_user)

@hackathon_bp.route('/hackathons/create', methods=['GET', 'POST'])
@login_required
def create_hackathon(current_user):
    if request.method == 'GET':
        return render_template('hackathon/create.html', user=current_user)
    
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('Hackathon name is required.', 'error')
        return render_template('hackathon/create.html', user=current_user)
    
    try:
        new_hackathon = Hackathon(
            name=name,
            description=description,
            user_id=current_user.id
        )
        db.session.add(new_hackathon)
        db.session.commit()
        
        flash(f'Hackathon "{name}" created successfully!', 'success')
        return redirect(url_for('hackathon.hackathon_detail', id=new_hackathon.id))
    except Exception as e:
        db.session.rollback()
        flash('Failed to create hackathon. Please try again.', 'error')
        return render_template('hackathon/create.html', user=current_user)

@hackathon_bp.route('/hackathons/<int:id>')
@login_required
def hackathon_detail(current_user, id):
    hackathon = Hackathon.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Get counts for stats
    template_count = len(hackathon.certificate_templates)
    participant_count = len(hackathon.participants)
    sent_count = len([p for p in hackathon.participants if p.certificate_sent])
    
    return render_template('hackathon/detail.html', 
                         hackathon=hackathon, 
                         user=current_user,
                         template_count=template_count,
                         participant_count=participant_count,
                         sent_count=sent_count)

@hackathon_bp.route('/hackathons/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_hackathon(current_user, id):
    hackathon = Hackathon.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'GET':
        return render_template('hackathon/edit.html', hackathon=hackathon, user=current_user)
    
    name = request.form.get('name')
    description = request.form.get('description')
    resubmission_form_link = request.form.get('resubmission_form_link')
    feedback_form_link = request.form.get('feedback_form_link')
    
    if not name:
        flash('Hackathon name is required.', 'error')
        return render_template('hackathon/edit.html', hackathon=hackathon, user=current_user)
    
    try:
        hackathon.name = name
        hackathon.description = description
        hackathon.resubmission_form_link = resubmission_form_link if resubmission_form_link else None
        hackathon.feedback_form_link = feedback_form_link if feedback_form_link else None
        db.session.commit()
        
        flash(f'Hackathon "{name}" updated successfully!', 'success')
        return redirect(url_for('hackathon.hackathon_detail', id=hackathon.id))
    except Exception as e:
        db.session.rollback()
        flash('Failed to update hackathon. Please try again.', 'error')
        return render_template('hackathon/edit.html', hackathon=hackathon, user=current_user)

@hackathon_bp.route('/hackathons/<int:id>/delete', methods=['POST'])
@login_required
def delete_hackathon(current_user, id):
    hackathon = Hackathon.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        hackathon_name = hackathon.name
        db.session.delete(hackathon)
        db.session.commit()
        
        flash(f'Hackathon "{hackathon_name}" deleted successfully!', 'success')
        return redirect(url_for('hackathon.list_hackathons'))
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete hackathon. Please try again.', 'error')
        return redirect(url_for('hackathon.hackathon_detail', id=id))
