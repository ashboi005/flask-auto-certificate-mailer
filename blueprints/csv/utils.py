import pandas as pd
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

ALLOWED_CSV_EXTENSIONS = {'csv'}
CSV_UPLOAD_FOLDER = 'uploads/csv'

def allowed_csv_file(filename):
    """Check if uploaded file is a valid CSV"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_CSV_EXTENSIONS

def process_csv_file(file_path):
    """
    Process uploaded CSV file and extract names and emails from team registration format
    Expected columns: Team-based registration with up to 3 members per team
    """
    try:
        print(f"DEBUG: Processing CSV file: {file_path}")
        
        # Read CSV file
        df = pd.read_csv(file_path)
        
        print(f"DEBUG: CSV shape: {df.shape}")
        print(f"DEBUG: Original columns: {df.columns.tolist()}")
        
        # Convert column names to lowercase for easier matching
        df.columns = df.columns.str.lower().str.strip()
        
        # Expected column patterns for team registration
        member_patterns = [
            {'name': 'name of 1st member:', 'email': 'email of 1st member:'},
            {'name': 'name of 2nd member:', 'email': 'email of 2nd member:'},
            {'name': 'name of 3rd member:', 'email': 'email of 3rd member:'}
        ]
        
        # Find the actual column names that match our patterns
        found_columns = []
        available_cols = df.columns.tolist()
        
        for i, pattern in enumerate(member_patterns):
            name_col = None
            email_col = None
            
            # Find name column (flexible matching)
            for col in available_cols:
                if f'{i+1}st member' in col or f'{i+1}nd member' in col or f'{i+1}rd member' in col:
                    if 'name' in col:
                        name_col = col
                    elif 'email' in col:
                        email_col = col
            
            if name_col and email_col:
                found_columns.append({'name': name_col, 'email': email_col, 'member_num': i+1})
                print(f"DEBUG: Found member {i+1} columns - Name: {name_col}, Email: {email_col}")
        
        if not found_columns:
            return {
                'success': False,
                'error': "Could not find team member columns. Expected format: 'Name of 1st Member:', 'Email of 1st Member:', etc.",
                'available_columns': available_cols
            }
        
        print(f"DEBUG: Found {len(found_columns)} member column sets")
        
        # Extract participants from each team row
        participants = []
        invalid_emails = []
        team_count = 0
        
        # Email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for index, row in df.iterrows():
            team_count += 1
            team_name = row.get('team name (leave empty if solo)', f'Team {team_count}')
            
            # Process each member in the team
            for member_info in found_columns:
                name_col = member_info['name']
                email_col = member_info['email']
                member_num = member_info['member_num']
                
                # Get name and email for this member
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
                            if email not in [p['email'] for p in participants]:
                                participants.append({
                                    'name': name,
                                    'email': email,
                                    'team_name': str(team_name).strip() if pd.notna(team_name) else f'Team {team_count}',
                                    'member_position': member_num
                                })
                                print(f"DEBUG: Added participant: {name} ({email}) from {team_name}")
                            else:
                                print(f"DEBUG: Duplicate email skipped: {email}")
                        else:
                            invalid_emails.append(email)
                            print(f"DEBUG: Invalid email format: {email}")
        
        result = {
            'success': True,
            'participants': participants,
            'total_teams': team_count,
            'total_participants': len(participants),
            'invalid_count': len(invalid_emails),
            'invalid_emails': invalid_emails
        }
        
        print(f"DEBUG: Final result: {len(participants)} participants from {team_count} teams")
        return result
        
    except Exception as e:
        print(f"ERROR processing CSV: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': f"Error processing CSV file: {str(e)}"
        }

def save_csv_file(file, hackathon_id):
    """Save uploaded CSV file"""
    if file and allowed_csv_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to prevent conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        # Create directory if it doesn't exist
        upload_dir = os.path.join(CSV_UPLOAD_FOLDER, str(hackathon_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        print(f"DEBUG: Saved CSV file to: {file_path}")
        return file_path
    return None

def get_csv_sample_format():
    """Return sample CSV format for user reference"""
    return {
        'headers': [
            'Timestamp', 
            'Team Name (leave empty if solo)', 
            'Number of Members', 
            'Name of 1st Member:', 
            'Contact Number of 1st Member:', 
            'Email of 1st Member:',
            'Name of 2nd Member:', 
            'Contact Number of 2nd Member:', 
            'Email of 2nd Member:',
            'Name of 3rd Member:', 
            'Contact Number of 3rd Member:', 
            'Email of 3rd Member:'
        ],
        'sample_data': [
            ['2024-01-15 10:30:00', 'Team Alpha', '3', 'John Doe', '1234567890', 'john.doe@example.com', 'Jane Smith', '0987654321', 'jane.smith@example.com', 'Bob Johnson', '1122334455', 'bob.johnson@example.com'],
            ['2024-01-15 11:00:00', 'Solo Participant', '1', 'Alice Brown', '5566778899', 'alice.brown@example.com', '', '', '', '', '', ''],
            ['2024-01-15 11:30:00', 'Team Beta', '2', 'Charlie Wilson', '2233445566', 'charlie.wilson@example.com', 'Diana Prince', '7788990011', 'diana.prince@example.com', '', '', '']
        ],
        'description': 'CSV should contain team registration data. Each row represents a team with 1-3 members. All members will be extracted as individual participants.'
    }
