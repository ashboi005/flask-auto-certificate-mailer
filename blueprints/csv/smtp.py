import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class EmailSender:
    def __init__(self):
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.email_address = os.environ.get('EMAIL_ADDRESS')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.from_name = os.environ.get('EMAIL_FROM_NAME', 'Certificate Sender')
        
        if not self.email_address or not self.email_password:
            raise ValueError("Email credentials not configured. Please set EMAIL_ADDRESS and EMAIL_PASSWORD in .env file")
        
        print(f"DEBUG: Email sender initialized - {self.email_address} via {self.smtp_server}:{self.smtp_port}")
    
    def create_certificate_email(self, recipient_name, recipient_email, hackathon_name, certificate_path, feedback_link=None):
        """Create email with certificate attachment"""
        try:
            msg = MIMEMultipart()
            
            # Email headers
            msg['From'] = f"{self.from_name} <{self.email_address}>"
            msg['To'] = recipient_email
            msg['Subject'] = f"🎉 Your Certificate for {hackathon_name}"
            
            # Email body
            feedback_section = ""
            if feedback_link:
                feedback_section = f"""

We would also appreciate if you gave an anonymous feedback about the hackathon experience:
🔗 Anonymous Feedback Form: {feedback_link}
"""
            
            body = f"""Dear {recipient_name},

Congratulations! 🎉

We are pleased to share your certificate for {hackathon_name}. Thank you for your participation and contribution to making this event a success.

Your certificate is attached to this email as a high-quality image file.
{feedback_section}
Best regards,
{self.from_name}

This is an automated email. Please do not reply to this message.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach certificate PNG
            if os.path.exists(certificate_path):
                with open(certificate_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    
                    # Clean filename for attachment - detect file type
                    file_ext = os.path.splitext(certificate_path)[1].lower()
                    if file_ext == '.png':
                        clean_name = f"{recipient_name.replace(' ', '_')}_certificate.png"
                    else:
                        clean_name = f"{recipient_name.replace(' ', '_')}_certificate{file_ext}"
                    
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= "{clean_name}"',
                    )
                    msg.attach(part)
                    
                print(f"DEBUG: Certificate attached: {certificate_path}")
            else:
                print(f"ERROR: Certificate file not found: {certificate_path}")
                return None
            
            return msg
            
        except Exception as e:
            print(f"ERROR creating email: {e}")
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
    
    def send_certificate(self, recipient_name, recipient_email, hackathon_name, certificate_path, feedback_link=None):
        """Send certificate to a single recipient"""
        print(f"DEBUG: Preparing to send certificate to {recipient_name} ({recipient_email})")
        
        msg = self.create_certificate_email(recipient_name, recipient_email, hackathon_name, certificate_path, feedback_link)
        if msg:
            return self.send_email(msg)
        return {'success': False, 'error': 'Failed to create email'}
    
    def send_bulk_certificates(self, participants_data, hackathon_name, feedback_link=None, progress_callback=None):
        """
        Send certificates to multiple participants
        participants_data: list of dict with 'name', 'email', 'certificate_path'
        """
        print(f"DEBUG: Starting bulk certificate sending for {len(participants_data)} participants")
        
        results = {
            'total': len(participants_data),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, participant in enumerate(participants_data):
            try:
                print(f"DEBUG: Processing participant {i+1}/{len(participants_data)}")
                
                result = self.send_certificate(
                    participant['name'],
                    participant['email'],
                    hackathon_name,
                    participant['certificate_path'],
                    feedback_link
                )
                
                if result['success']:
                    results['sent'] += 1
                    print(f"✅ Sent certificate to {participant['name']} ({participant['email']})")
                else:
                    results['failed'] += 1
                    error_msg = f"Failed to send to {participant['name']} ({participant['email']}): {result.get('error', 'Unknown error')}"
                    results['errors'].append(error_msg)
                    print(f"❌ {error_msg}")
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, len(participants_data), participant['name'])
                    
            except Exception as e:
                results['failed'] += 1
                error_msg = f"Exception sending to {participant['name']} ({participant['email']}): {str(e)}"
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
    
    def create_uncompletion_email(self, recipient_name, recipient_email, hackathon_name, completion_remarks, resubmission_link, feedback_link=None):
        """Create email for project uncompletion notification"""
        try:
            msg = MIMEMultipart()
            
            # Email headers
            msg['From'] = f"{self.from_name} <{self.email_address}>"
            msg['To'] = recipient_email
            msg['Subject'] = f"Project Resubmission Required - {hackathon_name}"
            
            # Email body
            feedback_section = ""
            if feedback_link:
                feedback_section = f"""
We would also appreciate if you gave an anonymous feedback about the hackathon experience:
🔗 Anonymous Feedback Form: {feedback_link}
"""
            
            body = f"""Dear {recipient_name},

Thank you for participating in {hackathon_name}! 

We have reviewed your project submission and found that it requires some improvements before we can issue your completion certificate.

📝 Completion Remarks:
{completion_remarks}

To receive your certificate, please address the above points and resubmit your project using the link below:
🔗 Resubmission Form: {resubmission_link}
{feedback_section}
We look forward to seeing your improved submission!

Best regards,
{self.from_name}

---
This is an automated email. Please do not reply to this message.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            return msg
            
        except Exception as e:
            print(f"ERROR creating uncompletion email: {e}")
            return None

    def send_uncompletion_email(self, recipient_name, recipient_email, hackathon_name, completion_remarks, resubmission_link, feedback_link=None):
        """Send uncompletion email to a single recipient"""
        print(f"DEBUG: Preparing to send uncompletion email to {recipient_name} ({recipient_email})")
        
        msg = self.create_uncompletion_email(recipient_name, recipient_email, hackathon_name, completion_remarks, resubmission_link, feedback_link)
        if msg:
            return self.send_email(msg)
        return {'success': False, 'error': 'Failed to create uncompletion email'}

    def send_bulk_uncompletion_emails(self, participants_data, hackathon_name, resubmission_link, feedback_link=None, progress_callback=None):
        """
        Send uncompletion emails to multiple participants
        participants_data: list of dict with 'name', 'email', 'completion_remarks'
        """
        print(f"DEBUG: Starting bulk uncompletion email sending for {len(participants_data)} participants")
        
        results = {
            'total': len(participants_data),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, participant in enumerate(participants_data):
            try:
                print(f"DEBUG: Processing participant {i+1}/{len(participants_data)}")
                
                result = self.send_uncompletion_email(
                    participant['name'],
                    participant['email'],
                    hackathon_name,
                    participant['completion_remarks'],
                    resubmission_link,
                    feedback_link
                )
                
                if result['success']:
                    results['sent'] += 1
                    print(f"✅ Sent uncompletion email to {participant['name']} ({participant['email']})")
                else:
                    results['failed'] += 1
                    error_msg = f"Failed to send uncompletion email to {participant['name']} ({participant['email']}): {result.get('error', 'Unknown error')}"
                    results['errors'].append(error_msg)
                    print(f"❌ {error_msg}")
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, len(participants_data), participant['name'])
                    
            except Exception as e:
                results['failed'] += 1
                error_msg = f"Exception sending uncompletion email to {participant['name']} ({participant['email']}): {str(e)}"
                results['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        print(f"DEBUG: Bulk uncompletion email sending completed. Sent: {results['sent']}, Failed: {results['failed']}")
        return results
