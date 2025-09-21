from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from blueprints.auth.decorators import login_required
from config import db
from models import Hackathon, Participant, CertificateTemplate
from .utils import process_csv_file, save_csv_file, get_csv_sample_format
from .smtp import EmailSender
from blueprints.certificates.utils import generate_certificate_with_name
from blueprints.certificates.utils import get_file_path, generate_certificate_with_name

csv_bp = Blueprint('csv', __name__)

@csv_bp.route('/hackathon/<int:hackathon_id>/participants')
@login_required
def list_participants(current_user, hackathon_id):
    """List all participants for a hackathon"""
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    participants = Participant.query.filter_by(hackathon_id=hackathon_id).all()
    templates = CertificateTemplate.query.filter_by(hackathon_id=hackathon_id).all()
    
    return render_template('csv/participants.html', 
                         hackathon=hackathon, 
                         participants=participants,
                         templates=templates,
                         user=current_user)

@csv_bp.route('/hackathon/<int:hackathon_id>/participants/upload', methods=['GET', 'POST'])
@login_required
def upload_csv(current_user, hackathon_id):
    """Upload CSV file with participants"""
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'GET':
        sample_format = get_csv_sample_format()
        return render_template('csv/upload.html', 
                             hackathon=hackathon, 
                             sample_format=sample_format,
                             user=current_user)
    
    # Handle POST request
    if 'csv_file' not in request.files:
        flash('No file selected', 'error')
        return redirect(request.url)
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(request.url)
    
    # Save and process CSV file
    file_path = save_csv_file(file, hackathon_id)
    if not file_path:
        flash('Invalid file type. Please upload a CSV file.', 'error')
        return redirect(request.url)
    
    # Process CSV file
    result = process_csv_file(file_path)
    
    if not result['success']:
        flash(f"Error processing CSV: {result['error']}", 'error')
        if 'available_columns' in result:
            flash(f"Available columns: {', '.join(result['available_columns'])}", 'info')
        return redirect(request.url)
    
    # Clear existing participants for this hackathon (optional - you might want to append instead)
    existing_count = Participant.query.filter_by(hackathon_id=hackathon_id).count()
    if existing_count > 0:
        if request.form.get('replace_existing') == 'yes':
            Participant.query.filter_by(hackathon_id=hackathon_id).delete()
            flash(f'Replaced {existing_count} existing participants', 'info')
    
    # Add new participants to database
    added_count = 0
    for participant_data in result['participants']:
        # Check if participant already exists (by email)
        existing = Participant.query.filter_by(
            email=participant_data['email'], 
            hackathon_id=hackathon_id
        ).first()
        
        if not existing:
            participant = Participant(
                name=participant_data['name'],
                email=participant_data['email'],
                hackathon_id=hackathon_id,
                team_name=participant_data.get('team_name'),
                member_position=participant_data.get('member_position'),
                completion_remarks=participant_data.get('completion_remarks', '')
            )
            db.session.add(participant)
            added_count += 1
        else:
            # Update completion remarks for existing participants
            existing.completion_remarks = participant_data.get('completion_remarks', '')
            db.session.add(existing)
    
    db.session.commit()
    
    # Show success message with stats
    success_msg = f"Successfully processed {result['total_participants']} participants from {result['total_teams']} teams"
    if added_count < result['total_participants']:
        success_msg += f" ({added_count} new, {result['total_participants'] - added_count} already existed)"
    
    if result['invalid_count'] > 0:
        success_msg += f" ({result['invalid_count']} invalid entries skipped)"
    
    flash(success_msg, 'success')
    
    if result['invalid_emails']:
        flash(f"Invalid emails skipped: {', '.join(result['invalid_emails'][:5])}", 'warning')
    
    return redirect(url_for('csv.list_participants', hackathon_id=hackathon_id))

@csv_bp.route('/hackathon/<int:hackathon_id>/participants/send', methods=['GET', 'POST'])
@login_required
def send_certificates(current_user, hackathon_id):
    """Send certificates to selected participants"""
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    participants = Participant.query.filter_by(hackathon_id=hackathon_id).all()
    templates = CertificateTemplate.query.filter_by(hackathon_id=hackathon_id).all()
    
    if not templates:
        flash('Please upload at least one certificate template before sending certificates.', 'error')
        return redirect(url_for('certificates.list_templates', hackathon_id=hackathon_id))
    
    if not participants:
        flash('No participants found. Please upload a CSV file with participant data first.', 'error')
        return redirect(url_for('csv.upload_csv', hackathon_id=hackathon_id))
    
    if request.method == 'GET':
        return render_template('csv/send.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             templates=templates,
                             user=current_user)
    
    # Handle POST request - send certificates
    selected_participants = request.form.getlist('participants')
    template_id = request.form.get('template_id')
    
    if not selected_participants:
        flash('Please select at least one participant.', 'error')
        return render_template('csv/send.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             templates=templates,
                             user=current_user)
    
    if not template_id:
        flash('Please select a certificate template.', 'error')
        return render_template('csv/send.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             templates=templates,
                             user=current_user)
    
    template = CertificateTemplate.query.get_or_404(template_id)
    
    # Start email sending process
    try:
        email_sender = EmailSender()
        
        # Test email connection first
        connection_test = email_sender.test_connection()
        if not connection_test['success']:
            flash(f"Email connection failed: {connection_test['error']}", 'error')
            return render_template('csv/send.html', 
                                 hackathon=hackathon, 
                                 participants=participants,
                                 templates=templates,
                                 user=current_user)
        
        participants_to_send = []
        
        # Generate certificates for selected participants
        for participant_id in selected_participants:
            participant = Participant.query.get(participant_id)
            if participant:
                # Generate certificate with participant's name
                certificate_path = generate_certificate_with_name(
                    hackathon_id, 
                    template.filename, 
                    participant.name,
                    template.name_x_position,
                    template.name_y_position,
                    template.font_size,
                    template.font_color
                )
                
                if certificate_path:
                    participants_to_send.append({
                        'name': participant.name,
                        'email': participant.email,
                        'certificate_path': certificate_path,
                        'participant_id': participant.id,
                        'completion_remarks': participant.completion_remarks
                    })
                else:
                    flash(f'Failed to generate certificate for {participant.name}', 'warning')
        
        if not participants_to_send:
            flash('Failed to generate certificates for any participant. Please try again.', 'error')
            return render_template('csv/send.html', 
                                 hackathon=hackathon, 
                                 participants=participants,
                                 templates=templates,
                                 user=current_user)
        
        # Send emails
        def progress_callback(current, total, name):
            print(f"Progress: {current}/{total} - Sending to {name}")
        
        results = email_sender.send_bulk_certificates(
            participants_to_send, 
            hackathon.name,
            hackathon.feedback_form_link,
            progress_callback
        )
        
        # Update database with sent status
        for participant_data in participants_to_send:
            participant = Participant.query.get(participant_data['participant_id'])
            if participant:
                participant.certificate_sent = True
                participant.certificate_template_id = template_id
                participant.sent_at = datetime.utcnow()
        
        db.session.commit()
        
        # Show results
        if results['sent'] > 0:
            flash(f"Successfully sent {results['sent']} certificates! 🎉", 'success')
        
        if results['failed'] > 0:
            flash(f"Failed to send {results['failed']} certificates.", 'error')
            for error in results['errors'][:3]:  # Show first 3 errors
                flash(error, 'warning')
        
        return redirect(url_for('csv.list_participants', hackathon_id=hackathon_id))
        
    except ValueError as e:
        flash(f"Email configuration error: {str(e)}", 'error')
        return render_template('csv/send.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             templates=templates,
                             user=current_user)
    except Exception as e:
        flash(f"Error sending certificates: {str(e)}", 'error')
        return render_template('csv/send.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             templates=templates,
                             user=current_user)

@csv_bp.route('/hackathon/<int:hackathon_id>/participants/send-uncompletion', methods=['GET', 'POST'])
@login_required
def send_uncompletion_emails(current_user, hackathon_id):
    """Send uncompletion emails to selected participants"""
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    participants = Participant.query.filter_by(hackathon_id=hackathon_id).all()
    
    if not participants:
        flash('No participants found. Please upload a CSV file with participant data first.', 'error')
        return redirect(url_for('csv.upload_csv', hackathon_id=hackathon_id))
    
    if not hackathon.resubmission_form_link:
        flash('Please configure the resubmission form link in hackathon settings before sending uncompletion emails.', 'error')
        return redirect(url_for('hackathon.edit_hackathon', id=hackathon_id))
    
    if request.method == 'GET':
        return render_template('csv/send_uncompletion.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             user=current_user)
    
    # Handle POST request - send uncompletion emails
    selected_participants = request.form.getlist('participants')
    
    if not selected_participants:
        flash('Please select at least one participant.', 'error')
        return render_template('csv/send_uncompletion.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             user=current_user)
    
    # Start email sending process
    try:
        email_sender = EmailSender()
        
        # Test email connection first
        connection_test = email_sender.test_connection()
        if not connection_test['success']:
            flash(f"Email connection failed: {connection_test['error']}", 'error')
            return render_template('csv/send_uncompletion.html', 
                                 hackathon=hackathon, 
                                 participants=participants,
                                 user=current_user)
        
        participants_to_send = []
        
        # Prepare participants for uncompletion emails
        for participant_id in selected_participants:
            participant = Participant.query.get(participant_id)
            if participant:
                participants_to_send.append({
                    'name': participant.name,
                    'email': participant.email,
                    'completion_remarks': participant.completion_remarks or 'No specific remarks provided.',
                    'participant_id': participant.id
                })
        
        if not participants_to_send:
            flash('No valid participants selected. Please try again.', 'error')
            return render_template('csv/send_uncompletion.html', 
                                 hackathon=hackathon, 
                                 participants=participants,
                                 user=current_user)
        
        # Send uncompletion emails
        def progress_callback(current, total, name):
            print(f"Progress: {current}/{total} - Sending uncompletion email to {name}")
        
        results = email_sender.send_bulk_uncompletion_emails(
            participants_to_send, 
            hackathon.name,
            hackathon.resubmission_form_link,
            hackathon.feedback_form_link,
            progress_callback
        )
        
        # Update database with uncompletion email sent status
        for participant_data in participants_to_send:
            participant = Participant.query.get(participant_data['participant_id'])
            if participant:
                participant.uncompletion_email_sent = True
                participant.uncompletion_email_sent_at = datetime.utcnow()
        
        db.session.commit()
        
        # Show results
        if results['sent'] > 0:
            flash(f"Successfully sent {results['sent']} uncompletion emails! 📧", 'success')
        
        if results['failed'] > 0:
            flash(f"Failed to send {results['failed']} uncompletion emails.", 'error')
            for error in results['errors'][:3]:  # Show first 3 errors
                flash(error, 'warning')
        
        return redirect(url_for('csv.list_participants', hackathon_id=hackathon_id))
        
    except ValueError as e:
        flash(f"Email configuration error: {str(e)}", 'error')
        return render_template('csv/send_uncompletion.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             user=current_user)
    except Exception as e:
        flash(f"Error sending uncompletion emails: {str(e)}", 'error')
        return render_template('csv/send_uncompletion.html', 
                             hackathon=hackathon, 
                             participants=participants,
                             user=current_user)

@csv_bp.route('/hackathon/<int:hackathon_id>/participants/<int:participant_id>/delete', methods=['POST'])
@login_required
def delete_participant(current_user, hackathon_id, participant_id):
    """Delete a single participant"""
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    participant = Participant.query.filter_by(id=participant_id, hackathon_id=hackathon_id).first_or_404()
    
    participant_name = participant.name
    db.session.delete(participant)
    db.session.commit()
    
    flash(f'Participant "{participant_name}" deleted successfully.', 'success')
    return redirect(url_for('csv.list_participants', hackathon_id=hackathon_id))

@csv_bp.route('/hackathon/<int:hackathon_id>/participants/clear', methods=['POST'])
@login_required
def clear_all_participants(current_user, hackathon_id):
    """Clear all participants for a hackathon"""
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    
    count = Participant.query.filter_by(hackathon_id=hackathon_id).count()
    Participant.query.filter_by(hackathon_id=hackathon_id).delete()
    db.session.commit()
    
    flash(f'Cleared {count} participants successfully.', 'success')
    return redirect(url_for('csv.list_participants', hackathon_id=hackathon_id))
