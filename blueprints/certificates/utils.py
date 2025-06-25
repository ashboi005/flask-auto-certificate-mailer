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
    """Generate a certificate PDF with participant's name"""
    try:
        print(f"DEBUG: Generating certificate for {participant_name}")
        
        # Get paths
        pdf_path = get_file_path(hackathon_id, template_filename)
        print(f"DEBUG: Source PDF: {pdf_path}")
        
        # Create output directory
        certificate_dir = os.path.join('uploads', 'certificates', str(hackathon_id), 'generated')
        os.makedirs(certificate_dir, exist_ok=True)
        
        # Create unique filename for this participant
        safe_name = "".join(c for c in participant_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        certificate_name = f"{safe_name}_certificate.pdf"
        certificate_path = os.path.join(certificate_dir, certificate_name)
        
        print(f"DEBUG: Output certificate: {certificate_path}")
        
        # Open the source PDF and add text
        doc = fitz.open(pdf_path)
        page = doc[0]  # Get first page
        
        # Get page dimensions
        page_rect = page.mediabox
        page_width = page_rect.width
        page_height = page_rect.height
        
        print(f"DEBUG: PDF page dimensions: {page_width} x {page_height}")
        
        # Convert font color from hex to RGB
        if font_color.startswith('#'):
            font_color = font_color[1:]
        r = int(font_color[0:2], 16) / 255.0
        g = int(font_color[2:4], 16) / 255.0
        b = int(font_color[4:6], 16) / 255.0
        
        # Convert Y coordinate from image coordinate system to PDF coordinate system
        # The preview works on 2x scaled image, let's use the same approach
        # In images: Y=0 is top, in PDF: Y=0 is bottom
        scale_factor = 2.0  # This matches the scale used in pdf_to_image
        
        # Simple approach: just scale down and flip Y coordinate
        # This is exactly what we need to match the preview positioning
        pdf_y_position = page_height - (y_position / scale_factor)
        
        # Font size conversion: preview uses 2x scale, PDF uses 1x scale
        pdf_font_size = font_size / scale_factor
        
        print(f"DEBUG: PDF page dimensions: {page_width} x {page_height}")
        print(f"DEBUG: Image Y from top: {y_position}")
        print(f"DEBUG: Scaled down Y: {y_position / scale_factor}")
        print(f"DEBUG: PDF Y from bottom: {pdf_y_position}")
        print(f"DEBUG: Font sizes - Image: {font_size}, PDF: {pdf_font_size}")
        
        # Calculate accurate text width for centering using the scaled font size
        text_width = fitz.get_text_length(participant_name, fontname="helv", fontsize=pdf_font_size)
        pdf_x_position = (page_width - text_width) / 2  # Center horizontally
        
        print(f"DEBUG: Text width: {text_width}, Centered X: {pdf_x_position}")
        print(f"DEBUG: Final position: ({pdf_x_position}, {pdf_y_position})")
        print(f"DEBUG: Color: RGB({r}, {g}, {b})")
        
        # Add text to the PDF
        page.insert_text(
            (pdf_x_position, pdf_y_position),  # Position (centered X, converted Y)
            participant_name,                   # Text
            fontsize=pdf_font_size,            # Scaled font size
            color=(r, g, b),                   # RGB color
            fontname="helv"                    # Font name (Helvetica)
        )
        
        # Save the modified PDF
        doc.save(certificate_path)
        doc.close()
        
        print(f"DEBUG: Successfully generated certificate with name: {certificate_path}")
        return certificate_path
        
    except Exception as e:
        print(f"ERROR generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return None
