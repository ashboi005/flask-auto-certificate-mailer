import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from blueprints.auth.decorators import login_required
from config import db
from models import Hackathon, CertificateTemplate
from .utils import save_uploaded_file, pdf_to_image, get_file_path, delete_certificate_files, add_text_to_image

certificates_bp = Blueprint('certificates', __name__)

@certificates_bp.route('/hackathon/<int:hackathon_id>/templates')
@login_required
def list_templates(current_user, hackathon_id):
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    templates = CertificateTemplate.query.filter_by(hackathon_id=hackathon_id).all()
    
    return render_template('certificates/list.html', 
                         hackathon=hackathon, 
                         templates=templates, 
                         user=current_user)

@certificates_bp.route('/hackathon/<int:hackathon_id>/templates/upload', methods=['GET', 'POST'])
@login_required
def upload_template(current_user, hackathon_id):
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'GET':
        return render_template('certificates/upload.html', hackathon=hackathon, user=current_user)
    
    # Handle POST request
    name = request.form.get('name')
    file = request.files.get('file')
    
    if not name:
        flash('Template name is required.', 'error')
        return render_template('certificates/upload.html', hackathon=hackathon, user=current_user)
    
    if not file or file.filename == '':
        flash('Please select a PDF file.', 'error')
        return render_template('certificates/upload.html', hackathon=hackathon, user=current_user)
    
    # Save file
    filename = save_uploaded_file(file, hackathon_id)
    if not filename:
        flash('Invalid file type. Please upload a PDF file.', 'error')
        return render_template('certificates/upload.html', hackathon=hackathon, user=current_user)
    
    try:
        # Convert PDF to image for preview
        pdf_path = get_file_path(hackathon_id, filename)
        preview_path = pdf_to_image(pdf_path)
        
        # Create template record
        template = CertificateTemplate(
            name=name,
            filename=filename,
            hackathon_id=hackathon_id,
            name_x_position=300,  # Default position
            name_y_position=400,
            font_size=24,
            font_color='#000000'
        )
        
        db.session.add(template)
        db.session.commit()
        
        flash(f'Certificate template "{name}" uploaded successfully!', 'success')
        return redirect(url_for('certificates.preview_template', 
                              hackathon_id=hackathon_id, 
                              template_id=template.id))
    
    except Exception as e:
        db.session.rollback()
        flash('Failed to upload template. Please try again.', 'error')
        return render_template('certificates/upload.html', hackathon=hackathon, user=current_user)

@certificates_bp.route('/hackathon/<int:hackathon_id>/templates/<int:template_id>/preview')
@login_required
def preview_template(current_user, hackathon_id, template_id):
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    template = CertificateTemplate.query.filter_by(id=template_id, hackathon_id=hackathon_id).first_or_404()
    
    return render_template('certificates/preview.html', 
                         hackathon=hackathon, 
                         template=template, 
                         user=current_user)

@certificates_bp.route('/hackathon/<int:hackathon_id>/templates/<int:template_id>/update-preview', methods=['POST'])
@login_required
def update_preview(current_user, hackathon_id, template_id):
    """AJAX endpoint to update preview with new settings"""
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    template = CertificateTemplate.query.filter_by(id=template_id, hackathon_id=hackathon_id).first_or_404()
    
    # Get parameters from request
    sample_name = request.json.get('sample_name', 'John Doe')
    x_position = int(request.json.get('x_position', template.name_x_position))
    y_position = int(request.json.get('y_position', template.name_y_position))
    font_size = int(request.json.get('font_size', template.font_size))
    font_color = request.json.get('font_color', template.font_color)
    
    print(f"DEBUG: Update preview called with: {sample_name}, ({x_position}, {y_position}), {font_size}px, {font_color}")
    
    try:
        # Get file paths
        pdf_path = get_file_path(hackathon_id, template.filename)
        preview_path = pdf_path.replace('.pdf', '_preview.png')
        
        print(f"DEBUG: PDF path: {pdf_path}")
        print(f"DEBUG: Preview path: {preview_path}")
        print(f"DEBUG: Preview exists: {os.path.exists(preview_path)}")
        
        # Create preview with text (auto-centered on X-axis)
        temp_path = add_text_to_image(preview_path, sample_name, x_position, y_position, font_size, font_color, center_x=True)
        
        # Return relative path for frontend - normalize path separators
        relative_path = temp_path.replace('\\', '/').replace('uploads/', '/uploads/')
        
        print(f"DEBUG: Generated temp path: {temp_path}")
        print(f"DEBUG: Relative path: {relative_path}")
        print(f"DEBUG: Temp file exists: {os.path.exists(temp_path)}")
        
        return jsonify({
            'success': True,
            'preview_url': relative_path
        })
    
    except Exception as e:
        print(f"ERROR in update_preview: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@certificates_bp.route('/hackathon/<int:hackathon_id>/templates/<int:template_id>/save', methods=['POST'])
@login_required
def save_template_settings(current_user, hackathon_id, template_id):
    """Save template positioning and styling settings"""
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    template = CertificateTemplate.query.filter_by(id=template_id, hackathon_id=hackathon_id).first_or_404()
    
    try:
        # Update template settings
        template.name_x_position = float(request.form.get('x_position', template.name_x_position))
        template.name_y_position = float(request.form.get('y_position', template.name_y_position))
        template.font_size = int(request.form.get('font_size', template.font_size))
        template.font_color = request.form.get('font_color', template.font_color)
        
        db.session.commit()
        flash('Template settings saved successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Failed to save template settings.', 'error')
    
    return redirect(url_for('certificates.preview_template', 
                          hackathon_id=hackathon_id, 
                          template_id=template_id))

@certificates_bp.route('/hackathon/<int:hackathon_id>/templates/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(current_user, hackathon_id, template_id):
    hackathon = Hackathon.query.filter_by(id=hackathon_id, user_id=current_user.id).first_or_404()
    template = CertificateTemplate.query.filter_by(id=template_id, hackathon_id=hackathon_id).first_or_404()
    
    try:
        # Delete files
        delete_certificate_files(hackathon_id, template.filename)
        
        # Delete database record
        template_name = template.name
        db.session.delete(template)
        db.session.commit()
        
        flash(f'Certificate template "{template_name}" deleted successfully!', 'success')
        return redirect(url_for('certificates.list_templates', hackathon_id=hackathon_id))
        
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete template.', 'error')
        return redirect(url_for('certificates.preview_template', 
                              hackathon_id=hackathon_id, 
                              template_id=template_id))

@certificates_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    try:
        file_path = os.path.join('uploads', filename)
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            print(f"DEBUG: File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f"ERROR serving file: {e}")
        return "Error serving file", 500
