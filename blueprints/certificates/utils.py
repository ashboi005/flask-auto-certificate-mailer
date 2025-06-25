import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF for PDF processing
from flask import current_app

ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = 'uploads/certificates'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, hackathon_id):
    """Save uploaded PDF file and return filename"""
    if file and allowed_file(file.filename):
        # Create unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Create hackathon-specific directory
        hackathon_dir = os.path.join(UPLOAD_FOLDER, str(hackathon_id))
        os.makedirs(hackathon_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(hackathon_dir, unique_filename)
        file.save(file_path)
        
        return unique_filename
    return None

def pdf_to_image(pdf_path, page_number=0):
    """Convert PDF page to image for preview"""
    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        
        # Convert to image
        mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Save preview image
        preview_path = pdf_path.replace('.pdf', '_preview.png')
        with open(preview_path, 'wb') as f:
            f.write(img_data)
        
        doc.close()
        return preview_path
    except Exception as e:
        print(f"Error converting PDF to image: {e}")
        return None

def add_text_to_image(image_path, text, x, y, font_size, font_color, center_x=True):
    """Add text overlay to image and return base64 encoded result"""
    try:
        print(f"DEBUG: Adding text '{text}' to image at {image_path}")
        
        # Open image
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # Try to use a better font, fall back to default
        font = None
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)  # Windows
        except:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)  # macOS
                except:
                    font = ImageFont.load_default()
        
        # Calculate text dimensions for centering
        if center_x:
            # Get text bounding box
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            image_width = img.width
            
            # Center the text horizontally
            x = (image_width - text_width) // 2
        
        # Add text
        draw.text((x, y), text, fill=font_color, font=font)
        
        # Save to temporary location
        temp_path = image_path.replace('_preview.png', '_preview_temp.png')
        img.save(temp_path)
        
        return temp_path
    except Exception as e:
        print(f"Error adding text to image: {e}")
        import traceback
        traceback.print_exc()
        return image_path

def get_file_path(hackathon_id, filename):
    """Get full file path"""
    return os.path.join(UPLOAD_FOLDER, str(hackathon_id), filename)

def delete_certificate_files(hackathon_id, filename):
    """Delete certificate PDF and preview image"""
    try:
        # Delete PDF
        pdf_path = get_file_path(hackathon_id, filename)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        # Delete preview image
        preview_path = pdf_path.replace('.pdf', '_preview.png')
        if os.path.exists(preview_path):
            os.remove(preview_path)
        
        # Delete temp image
        temp_path = pdf_path.replace('.pdf', '_temp.png')
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return True
    except Exception as e:
        print(f"Error deleting files: {e}")
        return False

def generate_certificate_with_name(hackathon_id, template_filename, participant_name, x_position, y_position, font_size, font_color):
    """Generate a certificate PDF with participant's name using the same method as preview"""
    try:
        print(f"DEBUG: Generating certificate for {participant_name}")
        
        # Get paths
        pdf_path = get_file_path(hackathon_id, template_filename)
        preview_path = pdf_path.replace('.pdf', '_preview.png')
        
        print(f"DEBUG: Source PDF: {pdf_path}")
        print(f"DEBUG: Preview image: {preview_path}")
        
        # Create output directory
        certificate_dir = os.path.join('uploads', 'certificates', str(hackathon_id), 'generated')
        os.makedirs(certificate_dir, exist_ok=True)
        
        # Create unique filename for this participant
        safe_name = "".join(c for c in participant_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        # Step 1: Use the EXACT same method as preview - add text to the preview image
        temp_image_path = add_text_to_image(
            preview_path, 
            participant_name, 
            x_position,  # We don't use this since we auto-center
            y_position, 
            font_size, 
            font_color, 
            center_x=True
        )
        
        print(f"DEBUG: Generated image with text: {temp_image_path}")
        
        # Step 2: Convert the image back to PDF
        certificate_name = f"{safe_name}_certificate.pdf"
        certificate_path = os.path.join(certificate_dir, certificate_name)
        
        # Convert image to PDF using PIL
        img = Image.open(temp_image_path)
        
        # Convert to RGB if necessary (for PDF compatibility)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as PDF
        img.save(certificate_path, 'PDF', resolution=150.0)
        img.close()
        
        print(f"DEBUG: Successfully generated certificate: {certificate_path}")
        return certificate_path
        
    except Exception as e:
        print(f"ERROR generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return None
