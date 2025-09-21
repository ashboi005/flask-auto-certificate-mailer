from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
import os
import json
from datetime import datetime

from blueprints.auth.decorators import login_required
from .utils import process_contacts_file, save_contacts_file, get_contacts_sample_format
from .email_sender import BulkEmailSender
from .template_utils import (
    save_email_template, get_user_templates, get_template_by_id,
    save_meet_link, get_user_meet_links, map_csv_to_template_variables,
    get_default_templates, TemplateProcessor
)
from .template_email_sender import TemplateEmailSender
from models import db

bulk_email_bp = Blueprint('bulk_email', __name__)

@bulk_email_bp.route('/bulk-email')
@login_required
def dashboard(current_user):
    """Bulk email dashboard"""
    return render_template('bulk_email/dashboard.html', user=current_user)

@bulk_email_bp.route('/bulk-email/upload', methods=['GET', 'POST'])
@login_required
def upload_contacts(current_user):
    """Upload contacts file (Excel/CSV)"""
    
    if request.method == 'GET':
        sample_format = get_contacts_sample_format()
        return render_template('bulk_email/upload.html', 
                             sample_format=sample_format,
                             user=current_user)
    
    # Handle POST request
    if 'contacts_file' not in request.files:
        flash('No file selected', 'error')
        return redirect(request.url)
    
    file = request.files['contacts_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(request.url)
    
    # Save and process file
    file_path = save_contacts_file(file, current_user.id)
    if not file_path:
        flash('Invalid file type. Please upload an Excel (.xlsx, .xls) or CSV file.', 'error')
        return redirect(request.url)
    
    # Process the file
    result = process_contacts_file(file_path)
    
    if not result['success']:
        flash(f"Error processing file: {result['error']}", 'error')
        return render_template('bulk_email/upload.html', 
                             sample_format=get_contacts_sample_format(),
                             user=current_user)
    
    # Store contacts in session for next step
    session['bulk_email_contacts'] = result['contacts']
    session['bulk_email_stats'] = {
        'total_contacts': result['total_contacts'],
        'invalid_count': result.get('invalid_count', 0),
        'skipped_rows': result.get('skipped_rows', 0),
        'name_column': result.get('name_column', 'Name'),
        'email_column': result.get('email_column', 'Email')
    }
    
    # Show success message with stats
    success_msg = f"Successfully processed {result['total_contacts']} contacts"
    if result.get('invalid_count', 0) > 0:
        success_msg += f" ({result['invalid_count']} invalid emails skipped)"
    if result.get('skipped_rows', 0) > 0:
        success_msg += f" ({result['skipped_rows']} empty rows skipped)"
    
    flash(success_msg, 'success')
    
    if result.get('invalid_emails'):
        flash(f"Invalid emails found: {', '.join(result['invalid_emails'][:5])}", 'warning')
    
    # Check if this is for template emails
    use_templates = request.form.get('use_templates', 'false') == 'true'
    if use_templates:
        return redirect(url_for('bulk_email.send_template_email'))
    
    return redirect(url_for('bulk_email.compose_email'))

@bulk_email_bp.route('/bulk-email/compose', methods=['GET', 'POST'])
@login_required
def compose_email(current_user):
    """Compose and send bulk email"""
    
    # Check if we have contacts in session
    contacts = session.get('bulk_email_contacts', [])
    stats = session.get('bulk_email_stats', {})
    
    if not contacts:
        flash('No contacts found. Please upload a contacts file first.', 'error')
        return redirect(url_for('bulk_email.upload_contacts'))
    
    if request.method == 'GET':
        return render_template('bulk_email/compose.html', 
                             contacts=contacts,
                             stats=stats,
                             user=current_user)
    
    # Handle POST request - send emails
    subject = request.form.get('subject', '').strip()
    custom_message = request.form.get('custom_message', '').strip()
    sender_name = request.form.get('sender_name', '').strip()
    
    if not subject:
        flash('Email subject is required.', 'error')
        return render_template('bulk_email/compose.html', 
                             contacts=contacts,
                             stats=stats,
                             user=current_user)
    
    if not custom_message:
        flash('Email message is required.', 'error')
        return render_template('bulk_email/compose.html', 
                             contacts=contacts,
                             stats=stats,
                             user=current_user)
    
    # Start email sending process
    try:
        email_sender = BulkEmailSender()
        
        # Test email connection first
        connection_test = email_sender.test_connection()
        if not connection_test['success']:
            flash(f"Email connection failed: {connection_test['error']}", 'error')
            return render_template('bulk_email/compose.html', 
                                 contacts=contacts,
                                 stats=stats,
                                 user=current_user)
        
        # Send emails
        def progress_callback(current, total, name):
            print(f"Progress: {current}/{total} - Sending to {name}")
        
        results = email_sender.send_bulk_custom_emails(
            contacts, 
            subject,
            custom_message,
            sender_name if sender_name else None,
            progress_callback
        )
        
        # Clear session data
        session.pop('bulk_email_contacts', None)
        session.pop('bulk_email_stats', None)
        
        # Show results
        if results['sent'] > 0:
            flash(f"Successfully sent {results['sent']} emails! 🎉", 'success')
        
        if results['failed'] > 0:
            flash(f"Failed to send {results['failed']} emails.", 'error')
            for error in results['errors'][:3]:  # Show first 3 errors
                flash(error, 'warning')
        
        return redirect(url_for('bulk_email.dashboard'))
        
    except ValueError as e:
        flash(f"Email configuration error: {str(e)}", 'error')
        return render_template('bulk_email/compose.html', 
                             contacts=contacts,
                             stats=stats,
                             user=current_user)
    except Exception as e:
        flash(f"Error sending emails: {str(e)}", 'error')
        return render_template('bulk_email/compose.html', 
                             contacts=contacts,
                             stats=stats,
                             user=current_user)

@bulk_email_bp.route('/bulk-email/preview')
@login_required
def preview_email(current_user):
    """Preview email with sample data"""
    
    contacts = session.get('bulk_email_contacts', [])
    if not contacts:
        return jsonify({'success': False, 'error': 'No contacts found'})
    
    subject = request.args.get('subject', '')
    custom_message = request.args.get('custom_message', '')
    sender_name = request.args.get('sender_name', '')
    
    # Use first contact for preview
    sample_contact = contacts[0]
    
    # Personalize the message
    personalized_message = custom_message.replace('{name}', sample_contact['name'])
    personalized_message = personalized_message.replace('{Name}', sample_contact['name'])
    personalized_message = personalized_message.replace('{NAME}', sample_contact['name'].upper())
    
    sender_display = sender_name if sender_name else 'Bulk Email Sender'
    
    preview_body = f"""Dear {sample_contact['name']},

{personalized_message}

Best regards,
{sender_display}

---
This is an automated email. Please do not reply to this message."""
    
    return jsonify({
        'success': True,
        'preview': {
            'to': sample_contact['email'],
            'subject': subject,
            'body': preview_body
        }
    })

# ===============================
# TEMPLATE-BASED EMAIL ROUTES
# ===============================

@bulk_email_bp.route('/bulk-email/templates')
@login_required
def template_dashboard(current_user):
    """Template management dashboard"""
    templates = get_user_templates(current_user.id)
    meet_links = get_user_meet_links(current_user.id)
    
    return render_template('bulk_email/templates/dashboard.html', 
                          templates=templates,
                          meet_links=meet_links,
                          user=current_user)

@bulk_email_bp.route('/bulk-email/templates/create', methods=['GET', 'POST'])
@login_required
def create_template(current_user):
    """Create new email template"""
    
    if request.method == 'GET':
        default_templates = get_default_templates()
        return render_template('bulk_email/templates/create.html', 
                             default_templates=default_templates,
                             user=current_user)
    
    # Handle POST request
    name = request.form.get('name', '').strip()
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not subject or not body:
        flash('Template name, subject and body are required.', 'error')
        return render_template('bulk_email/templates/create.html', 
                             default_templates=get_default_templates(),
                             user=current_user)
    
    # Extract static variables from form
    static_variables = {}
    for key, value in request.form.items():
        if key.startswith('static_') and value.strip():
            var_name = key[7:]  # Remove 'static_' prefix
            static_variables[var_name] = value.strip()
    
    # Save template
    result = save_email_template(name, subject, body, description, current_user.id, static_variables)
    
    if result['success']:
        flash(f'Template "{name}" created successfully! Found {len(result["variables"])} variables.', 'success')
        return redirect(url_for('bulk_email.template_dashboard'))
    else:
        flash(f'Error creating template: {result["error"]}', 'error')
        return render_template('bulk_email/templates/create.html', 
                             default_templates=get_default_templates(),
                             user=current_user)

@bulk_email_bp.route('/bulk-email/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(current_user, template_id):
    """Edit existing template"""
    
    template = get_template_by_id(template_id, current_user.id)
    if not template:
        flash('Template not found.', 'error')
        return redirect(url_for('bulk_email.template_dashboard'))
    
    if request.method == 'GET':
        return render_template('bulk_email/templates/edit.html', 
                             template=template,
                             user=current_user)
    
    # Handle POST request
    name = request.form.get('name', '').strip()
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not subject or not body:
        flash('Template name, subject and body are required.', 'error')
        return render_template('bulk_email/templates/edit.html', 
                             template=template,
                             user=current_user)
    
    # Update template
    try:
        from models import EmailTemplate
        db_template = EmailTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        
        if not db_template:
            flash('Template not found.', 'error')
            return redirect(url_for('bulk_email.template_dashboard'))
        
        # Validate template
        processor = TemplateProcessor()
        validation = processor.validate_template(subject, body)
        
        if not validation['valid']:
            flash(f'Template validation failed: {validation["error"]}', 'error')
            return render_template('bulk_email/templates/edit.html', 
                                 template=template,
                                 user=current_user)
        
        # Update template
        db_template.name = name
        db_template.subject = subject
        db_template.body = body
        db_template.description = description
        db_template.template_variables = json.dumps(validation['variables'])
        db_template.updated_at = datetime.utcnow()
        
        # Extract static variables from form
        static_variables = {}
        for key, value in request.form.items():
            if key.startswith('static_') and value.strip():
                var_name = key[7:]  # Remove 'static_' prefix
                static_variables[var_name] = value.strip()
        
        # Update static variables
        if static_variables:
            db_template.static_variables = json.dumps(static_variables)
        else:
            db_template.static_variables = None
        
        db.session.commit()
        
        flash(f'Template "{name}" updated successfully!', 'success')
        return redirect(url_for('bulk_email.template_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating template: {str(e)}', 'error')
        return render_template('bulk_email/templates/edit.html', 
                             template=template,
                             user=current_user)

@bulk_email_bp.route('/bulk-email/meet-links/create', methods=['POST'])
@login_required
def create_meet_link(current_user):
    """Create new Google Meet link"""
    
    name = request.form.get('name', '').strip()
    url = request.form.get('url', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not url:
        flash('Link name and URL are required.', 'error')
        return redirect(url_for('bulk_email.template_dashboard'))
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        flash('Please enter a valid URL starting with http:// or https://', 'error')
        return redirect(url_for('bulk_email.template_dashboard'))
    
    result = save_meet_link(name, url, description, current_user.id)
    
    if result['success']:
        flash(f'Meet link "{name}" saved successfully!', 'success')
    else:
        flash(f'Error saving meet link: {result["error"]}', 'error')
    
    return redirect(url_for('bulk_email.template_dashboard'))

@bulk_email_bp.route('/bulk-email/templates/send', methods=['GET', 'POST'])
@login_required
def send_template_email(current_user):
    """Send template-based emails"""
    
    # Check if we have contacts
    contacts = session.get('bulk_email_contacts', [])
    if not contacts:
        flash('No contacts found. Please upload a contacts file first.', 'error')
        return redirect(url_for('bulk_email.upload_contacts'))
    
    if request.method == 'GET':
        # Get user templates and meet links
        templates = get_user_templates(current_user.id)
        meet_links = get_user_meet_links(current_user.id)
        stats = session.get('bulk_email_stats', {})
        
        # Get CSV columns for mapping
        csv_columns = []
        if contacts:
            csv_columns = list(contacts[0].keys()) if contacts[0] else []
            print(f"DEBUG: contacts[0] = {contacts[0]}")  # Debug
            print(f"DEBUG: csv_columns = {csv_columns}")  # Debug
        else:
            print("DEBUG: No contacts found in session")  # Debug
        
        return render_template('bulk_email/templates/send.html',
                     templates=templates,
                     meet_links=meet_links,
                     contacts=contacts,  # Pass ALL contacts so user can select any
                     stats=stats,
                     csv_columns=csv_columns,
                     user=current_user)
    
    # Handle POST request - send template emails
    template_id = request.form.get('template_id')
    meet_link_id = request.form.get('meet_link_id')
    meet_link_custom = request.form.get('meet_link_custom', '').strip()
    sender_name = request.form.get('sender_name', '').strip()
    selected_contacts = request.form.getlist('selected_contacts')
    
    if not template_id:
        flash('Please select a template.', 'error')
        return redirect(request.url)
    
    # Get template
    template = get_template_by_id(int(template_id), current_user.id)
    if not template:
        flash('Template not found.', 'error')
        return redirect(url_for('bulk_email.template_dashboard'))
    
    # Get variable mappings
    variable_mappings = {}
    for var in template['variables']:
        mapping_key = f'mapping_{var}'
        if mapping_key in request.form:
            variable_mappings[var] = request.form[mapping_key]
    
    # AUTO-MAPPING FALLBACK: If no mappings provided, try auto-mapping
    if not variable_mappings:
        print("DEBUG: No explicit variable mappings found, attempting auto-mapping...")
        
        # Get available CSV columns
        csv_columns = []
        if contacts:
            csv_columns = list(contacts[0].keys()) if contacts[0] else []
        
        print(f"DEBUG: Available CSV columns for auto-mapping: {csv_columns}")
        
        # Auto-map variables to CSV columns with same or similar names
        for var in template['variables']:
            # Skip static variables
            if template.get('static_variables') and var in template['static_variables']:
                continue
                
            # Try exact match first
            if var in csv_columns:
                variable_mappings[var] = var
                print(f"DEBUG: Auto-mapped {var} -> {var} (exact match)")
            else:
                # Try fuzzy matching
                var_lower = var.lower()
                for col in csv_columns:
                    col_lower = col.lower()
                    if (var_lower in col_lower or col_lower in var_lower or
                        (var_lower.replace('_', '') in col_lower.replace('_', '')) or
                        (col_lower.replace('_', '') in var_lower.replace('_', ''))):
                        variable_mappings[var] = col
                        print(f"DEBUG: Auto-mapped {var} -> {col} (fuzzy match)")
                        break
    
    print(f"DEBUG: Template variables: {template['variables']}")
    print(f"DEBUG: Form data: {dict(request.form)}")
    print(f"DEBUG: Final variable mappings: {variable_mappings}")
    
    # Determine which contacts to send to
    if selected_contacts:
        # Filter contacts based on selection
        contacts_to_send = []
        selected_emails = set(selected_contacts)
        for contact in contacts:
            if contact['email'] in selected_emails:
                contacts_to_send.append(contact)
    else:
        contacts_to_send = contacts
    
    if not contacts_to_send:
        flash('No contacts selected for sending.', 'error')
        return redirect(request.url)
    
    # Determine meet link to use
    meet_link_url = None
    if meet_link_custom:
        meet_link_url = meet_link_custom
    elif meet_link_id:
        meet_links = get_user_meet_links(current_user.id)
        for link in meet_links:
            if link['id'] == int(meet_link_id):
                meet_link_url = link['url']
                break
    
    # Send template emails
    try:
        template_sender = TemplateEmailSender()
        
        # Test connection first
        connection_test = template_sender.test_connection()
        if not connection_test['success']:
            flash(f"Email connection failed: {connection_test['error']}", 'error')
            return redirect(request.url)
        
        # Prepare template data
        template_data = template.copy()
        template_data['user_id'] = current_user.id
        
        # Send emails with progress callback
        def progress_callback(current, total, name):
            print(f"Template Email Progress: {current}/{total} - Sending to {name}")
        
        results = template_sender.send_template_emails(
            template_data,
            contacts_to_send,
            variable_mappings,
            meet_link_url,
            sender_name,
            progress_callback
        )
        
        # Clear session data
        session.pop('bulk_email_contacts', None)
        session.pop('bulk_email_stats', None)
        
        # Show results
        if results['sent'] > 0:
            flash(f"Successfully sent {results['sent']} template emails using '{template['name']}'! 🎉", 'success')
        
        if results['failed'] > 0:
            flash(f"Failed to send {results['failed']} emails.", 'error')
            for error in results['errors'][:3]:  # Show first 3 errors
                flash(error, 'warning')
        
        return redirect(url_for('bulk_email.template_dashboard'))
        
    except Exception as e:
        flash(f"Error sending template emails: {str(e)}", 'error')
        return redirect(request.url)

@bulk_email_bp.route('/bulk-email/templates/<int:template_id>/preview')
@login_required
def preview_template(current_user, template_id):
    """Preview template with sample data"""
    
    template = get_template_by_id(template_id, current_user.id)
    if not template:
        return jsonify({'success': False, 'error': 'Template not found'})
    
    # Get sample data for variables
    processor = TemplateProcessor()
    sample_variables = processor.get_sample_variables(template['variables'])
    
    # Add static variables (these take priority over sample data)
    if 'static_variables' in template and template['static_variables']:
        sample_variables.update(template['static_variables'])
    
    # Get any additional sample data from query params
    for var in template['variables']:
        if var in request.args:
            sample_variables[var] = request.args[var]
    
    try:
        template_sender = TemplateEmailSender()
        preview_result = template_sender.preview_template_email(
            template['subject'],
            template['body'],
            sample_variables
        )
        
        if preview_result['success']:
            return jsonify({
                'success': True,
                'preview': preview_result['preview']
            })
        else:
            return jsonify({
                'success': False,
                'error': preview_result['error']
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
