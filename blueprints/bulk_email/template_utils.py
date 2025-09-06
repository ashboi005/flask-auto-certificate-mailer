import json
import re
from jinja2 import Template, Environment, meta
from flask import session
from models import EmailTemplate, MeetLink, TemplateEmailLog, db
from datetime import datetime

class TemplateProcessor:
    """Handles email template processing and variable extraction"""
    
    def __init__(self):
        self.env = Environment()
    
    def extract_variables(self, template_text):
        """Extract all variables from template text (both subject and body)"""
        # Find all {{variable}} patterns
        variables = set()
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        
        matches = re.findall(pattern, template_text)
        variables.update(matches)
        
        return list(variables)
    
    def validate_template(self, subject, body):
        """Validate template syntax"""
        try:
            # Test if templates can be parsed
            subject_template = Template(subject)
            body_template = Template(body)
            
            # Extract variables
            subject_vars = self.extract_variables(subject)
            body_vars = self.extract_variables(body)
            
            all_vars = list(set(subject_vars + body_vars))
            
            return {
                'valid': True,
                'variables': all_vars,
                'subject_variables': subject_vars,
                'body_variables': body_vars
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'variables': []
            }
    
    def render_template(self, subject, body, variables):
        """Render template with given variables"""
        try:
            subject_template = Template(subject)
            body_template = Template(body)
            
            rendered_subject = subject_template.render(**variables)
            rendered_body = body_template.render(**variables)
            
            return {
                'success': True,
                'subject': rendered_subject,
                'body': rendered_body
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sample_variables(self, variables, sample_contact=None):
        """Generate sample data for template preview"""
        sample_data = {}
        
        for var in variables:
            if var.lower() in ['name', 'participant_name', 'recipient_name']:
                sample_data[var] = sample_contact.get('name', 'John Doe') if sample_contact else 'John Doe'
            elif var.lower() in ['email', 'participant_email', 'recipient_email']:
                sample_data[var] = sample_contact.get('email', 'john@example.com') if sample_contact else 'john@example.com'
            elif 'time' in var.lower() or 'slot' in var.lower():
                sample_data[var] = '2:00 PM - 3:00 PM, Dec 15, 2025'
            elif 'meet' in var.lower() or 'link' in var.lower():
                sample_data[var] = 'https://meet.google.com/abc-defg-hij'
            elif 'date' in var.lower():
                sample_data[var] = 'December 15, 2025'
            elif 'position' in var.lower() or 'role' in var.lower():
                sample_data[var] = 'Software Developer'
            else:
                sample_data[var] = f'[{var.upper()}]'  # Placeholder format
        
        return sample_data

def save_email_template(name, subject, body, description, user_id, static_variables=None):
    """Save email template to database"""
    try:
        processor = TemplateProcessor()
        validation = processor.validate_template(subject, body)
        
        if not validation['valid']:
            return {'success': False, 'error': f"Template validation failed: {validation['error']}"}
        
        # Process static variables
        static_vars_json = None
        if static_variables:
            # Filter out empty values
            filtered_static_vars = {k: v for k, v in static_variables.items() if v.strip()}
            if filtered_static_vars:
                static_vars_json = json.dumps(filtered_static_vars)
        
        template = EmailTemplate(
            name=name,
            subject=subject,
            body=body,
            description=description,
            user_id=user_id,
            template_variables=json.dumps(validation['variables']),
            static_variables=static_vars_json
        )
        
        db.session.add(template)
        db.session.commit()
        
        return {
            'success': True,
            'template_id': template.id,
            'variables': validation['variables'],
            'static_variables': filtered_static_vars if static_variables else {}
        }
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}

def get_user_templates(user_id):
    """Get all templates for a user"""
    templates = EmailTemplate.query.filter_by(user_id=user_id).order_by(EmailTemplate.updated_at.desc()).all()
    
    template_list = []
    for template in templates:
        variables = json.loads(template.template_variables) if template.template_variables else []
        static_variables = json.loads(template.static_variables) if template.static_variables else {}
        template_list.append({
            'id': template.id,
            'name': template.name,
            'subject': template.subject,
            'body': template.body,
            'description': template.description,
            'variables': variables,
            'static_variables': static_variables,
            'created_at': template.created_at,
            'updated_at': template.updated_at
        })
    
    return template_list

def get_template_by_id(template_id, user_id):
    """Get specific template by ID for a user"""
    template = EmailTemplate.query.filter_by(id=template_id, user_id=user_id).first()
    if not template:
        return None
    
    variables = json.loads(template.template_variables) if template.template_variables else []
    static_variables = json.loads(template.static_variables) if template.static_variables else {}
    return {
        'id': template.id,
        'name': template.name,
        'subject': template.subject,
        'body': template.body,
        'description': template.description,
        'variables': variables,
        'static_variables': static_variables,
        'created_at': template.created_at,
        'updated_at': template.updated_at
    }

def save_meet_link(name, url, description, user_id):
    """Save Google Meet/Zoom link to database"""
    try:
        meet_link = MeetLink(
            name=name,
            url=url,
            description=description,
            user_id=user_id
        )
        
        db.session.add(meet_link)
        db.session.commit()
        
        return {'success': True, 'link_id': meet_link.id}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}

def get_user_meet_links(user_id):
    """Get all active meet links for a user"""
    links = MeetLink.query.filter_by(user_id=user_id, is_active=True).order_by(MeetLink.created_at.desc()).all()
    
    link_list = []
    for link in links:
        link_list.append({
            'id': link.id,
            'name': link.name,
            'url': link.url,
            'description': link.description,
            'created_at': link.created_at
        })
    
    return link_list

def map_csv_to_template_variables(csv_columns, template_variables):
    """Help map CSV columns to template variables"""
    # Automatic mapping suggestions
    mapping_suggestions = {}
    
    csv_lower = [col.lower() for col in csv_columns]
    
    for var in template_variables:
        var_lower = var.lower()
        
        # Try to find exact matches first
        if var_lower in csv_lower:
            mapping_suggestions[var] = csv_columns[csv_lower.index(var_lower)]
        # Try partial matches
        elif 'name' in var_lower:
            name_cols = [col for col in csv_columns if 'name' in col.lower()]
            if name_cols:
                mapping_suggestions[var] = name_cols[0]
        elif 'email' in var_lower:
            email_cols = [col for col in csv_columns if 'email' in col.lower()]
            if email_cols:
                mapping_suggestions[var] = email_cols[0]
        elif 'time' in var_lower or 'slot' in var_lower:
            time_cols = [col for col in csv_columns if any(word in col.lower() for word in ['time', 'slot', 'schedule'])]
            if time_cols:
                mapping_suggestions[var] = time_cols[0]
        elif 'meet' in var_lower or 'link' in var_lower:
            link_cols = [col for col in csv_columns if any(word in col.lower() for word in ['link', 'meet', 'zoom', 'url'])]
            if link_cols:
                mapping_suggestions[var] = link_cols[0]
    
    return mapping_suggestions

def log_template_email(template_id, recipient_email, recipient_name, subject_sent, body_sent, variables_used, user_id, status='sent', error_message=None):
    """Log sent template email"""
    try:
        log_entry = TemplateEmailLog(
            template_id=template_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject_sent=subject_sent,
            body_sent=body_sent,
            variables_used=json.dumps(variables_used),
            user_id=user_id,
            status=status,
            error_message=error_message
        )
        
        db.session.add(log_entry)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error logging template email: {e}")
        return False

def get_default_templates():
    """Get some default template examples for new users"""
    return [
        {
            'name': 'Interview Invitation',
            'subject': 'Interview Scheduled - {{position}} at {{company_name}}',
            'body': '''Dear {{name}},

Congratulations! You have been selected for an interview for the position of {{position}} at {{company_name}}.

Interview Details:
📅 Date & Time: {{time_slot}}
💻 Meeting Link: {{meet_link}}
⏱️ Duration: Approximately 45 minutes

Please join the meeting a few minutes early and ensure you have a stable internet connection.

If you have any questions or need to reschedule, please contact us immediately.

Best regards,
{{interviewer_name}}
{{company_name}} Recruitment Team''',
            'description': 'Template for scheduling job interviews with candidates'
        },
        {
            'name': 'Event Invitation',
            'subject': '🎉 You\'re Invited: {{event_name}}',
            'body': '''Hello {{name}},

You are cordially invited to {{event_name}}.

Event Details:
📅 Date: {{event_date}}
🕒 Time: {{event_time}}
📍 Venue: {{venue}}
💻 Online Link: {{meet_link}}

{{event_description}}

Please confirm your attendance by replying to this email.

Looking forward to seeing you there!

Best regards,
{{organizer_name}}''',
            'description': 'General event invitation template'
        },
        {
            'name': 'Meeting Reminder',
            'subject': 'Reminder: {{meeting_topic}} - {{time_slot}}',
            'body': '''Hi {{name}},

This is a friendly reminder about our upcoming meeting.

Meeting Details:
📋 Topic: {{meeting_topic}}
📅 Time: {{time_slot}}
💻 Join Link: {{meet_link}}
📄 Agenda: {{agenda}}

Please review any materials shared earlier and come prepared with your questions.

See you soon!

{{organizer_name}}''',
            'description': 'Template for meeting reminders'
        }
    ]
