import pandas as pd
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

ALLOWED_EXCEL_EXTENSIONS = {'xlsx', 'xls', 'csv'}
BULK_EMAIL_UPLOAD_FOLDER = 'uploads/bulk_email'

def allowed_excel_file(filename):
    """Check if uploaded file is a valid Excel or CSV"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXCEL_EXTENSIONS

def process_contacts_file(file_path):
    """
    Process uploaded Excel/CSV file and extract names and emails
    Expected format: First column = Names, Second column = Emails
    """
    try:
        print(f"DEBUG: Processing contacts file: {file_path}")
        
        # Determine file type and read accordingly
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
        else:  # Excel files
            df = pd.read_excel(file_path)
        
        print(f"DEBUG: File shape: {df.shape}")
        print(f"DEBUG: Columns: {df.columns.tolist()}")
        
        # Get the first two columns (names and emails)
        if len(df.columns) < 2:
            return {
                'success': False,
                'error': "File must have at least 2 columns (Name and Email)",
                'available_columns': df.columns.tolist()
            }
        
        # Use first two columns regardless of their names
        name_col = df.columns[0]
        email_col = df.columns[1]
        
        print(f"DEBUG: Using columns - Name: '{name_col}', Email: '{email_col}'")
        
        # Extract contacts
        contacts = []
        invalid_emails = []
        skipped_rows = 0
        
        # Email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for index, row in df.iterrows():
            name = row.get(name_col, '')
            email = row.get(email_col, '')
            
            # Clean the data
            if pd.notna(name) and pd.notna(email):
                name = str(name).strip().title()  # Capitalize name properly
                email = str(email).strip().lower()
                
                # Skip if either is empty
                if name and email:
                    # Validate email format
                    if re.match(email_pattern, email):
                        # Check for duplicates
                        if email not in [c['email'] for c in contacts]:
                            # Create contact dict with all columns
                            contact = {
                                'name': name,
                                'email': email
                            }
                            
                            # Add all other columns as well
                            for col in df.columns:
                                if col not in [name_col, email_col]:  # Don't duplicate name/email
                                    value = row.get(col, '')
                                    if pd.notna(value):
                                        contact[col] = str(value).strip()
                                    else:
                                        contact[col] = ''
                            
                            contacts.append(contact)
                            print(f"DEBUG: Added contact: {name} ({email})")
                        else:
                            print(f"DEBUG: Duplicate email skipped: {email}")
                    else:
                        invalid_emails.append(email)
                        print(f"DEBUG: Invalid email format: {email}")
                else:
                    skipped_rows += 1
            else:
                skipped_rows += 1
        
        result = {
            'success': True,
            'contacts': contacts,
            'total_contacts': len(contacts),
            'invalid_count': len(invalid_emails),
            'invalid_emails': invalid_emails,
            'skipped_rows': skipped_rows,
            'name_column': name_col,
            'email_column': email_col
        }
        
        print(f"DEBUG: Final result: {len(contacts)} contacts processed")
        return result
        
    except Exception as e:
        print(f"ERROR processing contacts file: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': f"Error processing file: {str(e)}"
        }

def save_contacts_file(file, user_id):
    """Save uploaded contacts file"""
    if file and allowed_excel_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to prevent conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{timestamp}_{name}{ext}"
        
        # Create directory if it doesn't exist
        upload_dir = os.path.join(BULK_EMAIL_UPLOAD_FOLDER, str(user_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        print(f"DEBUG: Saved contacts file to: {file_path}")
        return file_path
    return None

def get_contacts_sample_format():
    """Return sample format for contacts file"""
    return {
        'headers': ['Name', 'Email'],
        'sample_data': [
            ['John Doe', 'john.doe@example.com'],
            ['Jane Smith', 'jane.smith@example.com'],
            ['Bob Johnson', 'bob.johnson@example.com'],
            ['Alice Brown', 'alice.brown@example.com']
        ],
        'description': 'Excel/CSV file with names in first column and emails in second column. Additional columns will be ignored.'
    }
