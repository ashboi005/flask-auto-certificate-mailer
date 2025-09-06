import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from .template_utils import TemplateProcessor, log_template_email

class TemplateEmailSender:
    """Extended email sender for template-based emails"""
    
    def __init__(self):
        # Use the same SMTP configuration as bulk emails
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtpconnect.zoho.in')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.email_address = os.environ.get('EMAIL_ADDRESS')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.from_name = os.environ.get('EMAIL_FROM_NAME', 'Template Email Sender')
        self.from_address = os.environ.get('EMAIL_FROM_ADDRESS', self.email_address)
        
        if not self.email_address or not self.email_password:
            raise ValueError("Email credentials not configured. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in .env file")
        
        self.template_processor = TemplateProcessor()
        print(f"DEBUG: Template email sender initialized - {self.email_address} via {self.smtp_server}:{self.smtp_port}")
    
    def create_template_email(self, template_subject, template_body, variables, recipient_email, recipient_name, sender_name=None):
        """Create email using template and variables"""
        
        # Render template with variables
        render_result = self.template_processor.render_template(template_subject, template_body, variables)
        
        if not render_result['success']:
            raise ValueError(f"Template rendering failed: {render_result['error']}")
        
        # Create email message
        msg = MIMEMultipart()
        
        # Set sender
        sender_display = sender_name if sender_name else self.from_name
        from_address = self.from_address if self.from_address else self.email_address
        msg['From'] = f"{sender_display} <{from_address}>"
        msg['To'] = f"{recipient_name} <{recipient_email}>"
        msg['Subject'] = render_result['subject']
        
        # Create email body - use template content as-is without adding extra formatting
        email_body = render_result['body']
        
        msg.attach(MIMEText(email_body, 'plain'))
        
        return {
            'message': msg,
            'rendered_subject': render_result['subject'],
            'rendered_body': email_body
        }
    
    def test_connection(self):
        """Test SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            server.quit()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_template_emails(self, template_data, contacts, variable_mappings, meet_link_url=None, sender_name=None, progress_callback=None):
        """
        Send template-based emails to multiple contacts
        
        Args:
            template_data: Dict with 'subject', 'body', 'id', 'name'
            contacts: List of contact dictionaries from CSV
            variable_mappings: Dict mapping template variables to CSV columns
            meet_link_url: Optional Google Meet link to use for all emails
            sender_name: Optional sender name
            progress_callback: Optional callback function for progress updates
        """
        
        results = {
            'sent': 0,
            'failed': 0,
            'errors': [],
            'details': []
        }
        
        try:
            print(f"DEBUG: Connecting to SMTP server {self.smtp_server}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            
            total_contacts = len(contacts)
            
            for index, contact in enumerate(contacts, 1):
                try:
                    # Prepare variables for this contact
                    email_variables = {}
                    
                    print(f"DEBUG: Processing contact {index}: {contact}")
                    print(f"DEBUG: Variable mappings: {variable_mappings}")
                    print(f"DEBUG: Template static variables: {template_data.get('static_variables', {})}")
                    
                    # First, add static variables (these have priority and are the same for everyone)
                    if 'static_variables' in template_data and template_data['static_variables']:
                        email_variables.update(template_data['static_variables'])
                        print(f"DEBUG: Added static variables: {template_data['static_variables']}")
                    
                    # Map CSV data to template variables (only for variables not already set as static)
                    for template_var, csv_column in variable_mappings.items():
                        if template_var not in email_variables:  # Don't override static variables
                            if csv_column and csv_column in contact:
                                email_variables[template_var] = contact[csv_column]
                                print(f"DEBUG: Mapped {template_var} -> {csv_column} = {contact[csv_column]}")
                            else:
                                email_variables[template_var] = f'[{template_var.upper()}]'  # Placeholder if missing
                                print(f"DEBUG: Missing mapping for {template_var}, using placeholder")
                    
                    # Add special variables
                    if 'name' not in email_variables and 'name' in contact:
                        email_variables['name'] = contact['name']
                        print(f"DEBUG: Added name from contact: {contact['name']}")
                    if 'email' not in email_variables and 'email' in contact:
                        email_variables['email'] = contact['email']
                        print(f"DEBUG: Added email from contact: {contact['email']}")
                    
                    print(f"DEBUG: Final email variables for {contact['name']}: {email_variables}")
                    
                    # Add meet link if provided
                    if meet_link_url:
                        # Look for any variable that might be a meet link
                        meet_vars = [var for var in template_data.get('variables', []) if 'meet' in var.lower() or 'link' in var.lower()]
                        for meet_var in meet_vars:
                            email_variables[meet_var] = meet_link_url
                    
                    # Create and send email
                    email_result = self.create_template_email(
                        template_data['subject'],
                        template_data['body'],
                        email_variables,
                        contact['email'],
                        contact.get('name', 'Recipient'),
                        sender_name
                    )
                    
                    # Send the email
                    server.send_message(email_result['message'])
                    
                    # Log successful send
                    log_template_email(
                        template_data['id'],
                        contact['email'],
                        contact.get('name', 'Recipient'),
                        email_result['rendered_subject'],
                        email_result['rendered_body'],
                        email_variables,
                        template_data.get('user_id', 1),  # Will be set from routes
                        'sent'
                    )
                    
                    results['sent'] += 1
                    results['details'].append({
                        'email': contact['email'],
                        'name': contact.get('name', 'Recipient'),
                        'status': 'sent',
                        'variables_used': email_variables
                    })
                    
                    print(f"✅ Sent template email to {contact['email']}")
                    
                    if progress_callback:
                        progress_callback(index, total_contacts, contact.get('name', contact['email']))
                    
                except Exception as e:
                    error_msg = f"Failed to send to {contact.get('email', 'unknown')}: {str(e)}"
                    results['errors'].append(error_msg)
                    results['failed'] += 1
                    
                    # Log failed send
                    log_template_email(
                        template_data['id'],
                        contact.get('email', 'unknown'),
                        contact.get('name', 'Recipient'),
                        '',
                        '',
                        {},
                        template_data.get('user_id', 1),
                        'failed',
                        str(e)
                    )
                    
                    results['details'].append({
                        'email': contact.get('email', 'unknown'),
                        'name': contact.get('name', 'Recipient'),
                        'status': 'failed',
                        'error': str(e)
                    })
                    
                    print(f"❌ Failed to send to {contact.get('email', 'unknown')}: {str(e)}")
            
            server.quit()
            
        except Exception as e:
            error_msg = f"SMTP connection error: {str(e)}"
            results['errors'].append(error_msg)
            print(f"❌ SMTP Error: {str(e)}")
        
        return results
    
    def preview_template_email(self, template_subject, template_body, variables, recipient_name="John Doe"):
        """Generate preview of template email"""
        try:
            render_result = self.template_processor.render_template(template_subject, template_body, variables)
            
            if not render_result['success']:
                return {'success': False, 'error': render_result['error']}
            
            # Use template content as-is for preview without adding extra formatting
            email_body = render_result['body']
            
            return {
                'success': True,
                'preview': {
                    'subject': render_result['subject'],
                    'body': email_body,
                    'variables_used': variables
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
