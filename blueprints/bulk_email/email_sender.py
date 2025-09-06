import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class BulkEmailSender:
    def __init__(self):
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.zoho.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.email_address = os.environ.get('EMAIL_ADDRESS')  
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.from_address = os.environ.get('EMAIL_FROM_ADDRESS', self.email_address)  
        self.from_name = os.environ.get('EMAIL_FROM_NAME', 'Bulk Email Sender')
        
        if not self.email_address or not self.email_password:
            raise ValueError("Email credentials not configured. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in .env file")
        
        print(f"DEBUG: Bulk email sender initialized - Login: {self.email_address}, From: {self.from_address} via {self.smtp_server}:{self.smtp_port}")
    
    def create_custom_email(self, recipient_name, recipient_email, subject, custom_message, sender_name=None):
        """Create custom email with personalized content"""
        try:
            msg = MIMEMultipart()
            
            # Email headers
            sender_display = sender_name if sender_name else self.from_name
            msg['From'] = f"{sender_display} <{self.from_address}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Personalize the message by replacing {name} placeholder
            personalized_message = custom_message.replace('{name}', recipient_name)
            personalized_message = personalized_message.replace('{Name}', recipient_name)
            personalized_message = personalized_message.replace('{NAME}', recipient_name.upper())
            
            # Email body - use message as-is if it already contains greeting/signature
            if personalized_message.strip().lower().startswith('dear') or 'regards' in personalized_message.lower():
                # Message already has greeting/signature, use as-is
                body = personalized_message
            else:
                # Add default greeting and signature
                body = f"""Dear {recipient_name},

{personalized_message}

Best regards,
{sender_display}

---
This is an automated email. Please do not reply to this message."""
            
            msg.attach(MIMEText(body, 'plain'))
            
            return msg
            
        except Exception as e:
            print(f"ERROR creating custom email: {e}")
            return None
    
    def send_email(self, msg):
        """Send email using SMTP"""
        try:
            print(f"DEBUG: Connecting to SMTP server {self.smtp_server}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable security
            server.login(self.email_address, self.email_password)
            
            text = msg.as_string()
            server.sendmail(self.email_address, msg['To'], text)
            server.quit()
            
            print(f"DEBUG: Email sent successfully to {msg['To']}")
            return {'success': True}
            
        except Exception as e:
            print(f"ERROR sending email: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_custom_email(self, recipient_name, recipient_email, subject, custom_message, sender_name=None):
        """Send custom email to a single recipient"""
        print(f"DEBUG: Preparing to send custom email to {recipient_name} ({recipient_email})")
        
        msg = self.create_custom_email(recipient_name, recipient_email, subject, custom_message, sender_name)
        if msg:
            return self.send_email(msg)
        return {'success': False, 'error': 'Failed to create email'}
    
    def send_bulk_custom_emails(self, contacts, subject, custom_message, sender_name=None, progress_callback=None):
        """
        Send custom emails to multiple contacts
        contacts: list of dict with 'name' and 'email'
        """
        print(f"DEBUG: Starting bulk custom email sending for {len(contacts)} contacts")
        
        results = {
            'total': len(contacts),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, contact in enumerate(contacts):
            try:
                print(f"DEBUG: Processing contact {i+1}/{len(contacts)}")
                
                result = self.send_custom_email(
                    contact['name'],
                    contact['email'],
                    subject,
                    custom_message,
                    sender_name
                )
                
                if result['success']:
                    results['sent'] += 1
                    print(f"✅ Sent email to {contact['name']} ({contact['email']})")
                else:
                    results['failed'] += 1
                    error_msg = f"Failed to send to {contact['name']} ({contact['email']}): {result.get('error', 'Unknown error')}"
                    results['errors'].append(error_msg)
                    print(f"❌ {error_msg}")
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, len(contacts), contact['name'])
                    
            except Exception as e:
                results['failed'] += 1
                error_msg = f"Exception sending to {contact['name']} ({contact['email']}): {str(e)}"
                results['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        print(f"DEBUG: Bulk sending completed. Sent: {results['sent']}, Failed: {results['failed']}")
        return results
    
    def test_connection(self):
        """Test SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            server.quit()
            return {'success': True, 'message': 'SMTP connection successful'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
