import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF for PDF processing
from flask import current_app

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
UPLOAD_FOLDER = 'uploads/certificates'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, hackathon_id):
    """Save uploaded template file (PDF or image) and return filename"""
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

def template_to_image(template_path, page_number=0):
    """Convert template (PDF or image) to image for preview"""
    try:
        file_ext = os.path.splitext(template_path)[1].lower()
        
        if file_ext == '.pdf':
            # Handle PDF files
            doc = fitz.open(template_path)
            page = doc[page_number]
            
            # Convert to image with high quality
            mat = fitz.Matrix(3, 3)  # 3x zoom for even better quality
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Save preview image
            preview_path = template_path.replace('.pdf', '_preview.png')
            with open(preview_path, 'wb') as f:
                f.write(img_data)
            
            doc.close()
            return preview_path
        else:
            # Handle image files (PNG, JPEG, etc.)
            img = Image.open(template_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Ensure high resolution - don't resize smaller images
            # Only resize if image is very large (above 2400px width)
            max_width = 2400
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save preview image with maximum quality
            base, _ = os.path.splitext(template_path)
            preview_path = f"{base}_preview.png"
            img.save(preview_path, 'PNG', optimize=False, compress_level=0)
            img.close()
            
            return preview_path
            
    except Exception as e:
        print(f"Error converting template to image: {e}")
        import traceback
        traceback.print_exc()
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
        
        # Save to temporary location with highest quality
        temp_path = image_path.replace('_preview.png', '_preview_temp.png')
        
        # Save as PNG with no compression for maximum quality
        img.save(temp_path, 'PNG', optimize=False, compress_level=0)
        
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
    """Delete certificate template and preview image"""
    try:
        # Delete template file
        template_path = get_file_path(hackathon_id, filename)
        if os.path.exists(template_path):
            os.remove(template_path)
        
        # Delete preview image (works for both PDF and image templates)
        base, _ = os.path.splitext(template_path)
        preview_path = f"{base}_preview.png"
        if os.path.exists(preview_path):
            os.remove(preview_path)
        
        # Delete temp image
        temp_path = f"{base}_preview_temp.png"
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return True
    except Exception as e:
        print(f"Error deleting files: {e}")
        return False

def generate_certificate_with_name(hackathon_id, template_filename, participant_name, x_position, y_position, font_size, font_color):
    """Generate a certificate PNG with participant's name using the same method as preview"""
    try:
        print(f"DEBUG: Generating certificate for {participant_name}")
        
        # Get paths
        template_path = get_file_path(hackathon_id, template_filename)
        base, _ = os.path.splitext(template_path)
        preview_path = f"{base}_preview.png"
        
        print(f"DEBUG: Source template: {template_path}")
        print(f"DEBUG: Preview image: {preview_path}")
        
        # Create output directory
        certificate_dir = os.path.join('uploads', 'certificates', str(hackathon_id), 'generated')
        os.makedirs(certificate_dir, exist_ok=True)
        
        # Create unique filename for this participant
        safe_name = "".join(c for c in participant_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        # Generate high-quality PNG with text overlay
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
        
        # Create final certificate name (PNG format for best quality)
        certificate_name = f"{safe_name}_certificate.png"
        certificate_path = os.path.join(certificate_dir, certificate_name)
        
        # Copy the high-quality image to final location
        # Open and save to ensure highest quality
        img = Image.open(temp_image_path)
        
        # Save as PNG with maximum quality
        img.save(certificate_path, 'PNG', optimize=False)
        img.close()
        
        print(f"DEBUG: Successfully generated certificate: {certificate_path}")
        return certificate_path
        
    except Exception as e:
        print(f"ERROR generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_certificate_pdf_from_png(png_path, participant_name):
    """Convert the high-quality PNG certificate to PDF if needed"""
    try:
        # Create PDF version from PNG
        pdf_path = png_path.replace('.png', '.pdf')
        
        img = Image.open(png_path)
        
        # Convert to RGB if necessary (for PDF compatibility)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as PDF with high resolution
        img.save(pdf_path, 'PDF', resolution=300.0, quality=95)
        img.close()
        
        print(f"DEBUG: Generated PDF version: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"ERROR generating PDF from PNG: {e}")
        return None
