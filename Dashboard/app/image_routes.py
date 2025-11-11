from flask import Blueprint, render_template, request, jsonify, send_file
import os
import json
from datetime import datetime
import uuid
import cv2
import numpy as np
from PIL import Image
import io

image_bp = Blueprint('image', __name__, url_prefix='/image')

@image_bp.route('/')
def index():
    """Main Image page with tabs"""
    return render_template('image.html')

@image_bp.route('/edit')
def edit_image():
    """Edit Image tab"""
    return render_template('image.html', active_tab='edit')

@image_bp.route('/collage')
def photo_collage():
    """Photo Collage tab"""
    return render_template('image.html', active_tab='collage')

# API endpoints for image editing
@image_bp.route('/api/upload', methods=['POST'])
def upload_image():
    """Upload image for editing"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
        
        # Save to image_editor_files folder
        upload_folder = os.path.join('data', 'image_editor_files')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, file.filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'path': filepath
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# === COLLAGE HISTORY APIs ===
# Note: Collage creation is handled entirely on frontend using HTML Canvas
# for better performance and real-time editing experience
COLLAGE_HISTORY_DIR = os.path.join('data', 'collage_history')
COLLAGE_HISTORY_JSON = os.path.join('data', 'collage_history.json')

# Ensure directories exist
os.makedirs(COLLAGE_HISTORY_DIR, exist_ok=True)

@image_bp.route('/api/save-collage', methods=['POST'])
def save_collage():
    """Save collage and add to history"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file'}), 400
        
        image_file = request.files['image']
        image_count = request.form.get('imageCount', 0)
        layout = request.form.get('layout', 'unknown')
        
        # Generate unique ID
        collage_id = str(uuid.uuid4())
        
        # Save image
        image_path = os.path.join(COLLAGE_HISTORY_DIR, f'{collage_id}.png')
        image_file.save(image_path)
        
        # Load existing history
        history = []
        if os.path.exists(COLLAGE_HISTORY_JSON):
            with open(COLLAGE_HISTORY_JSON, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        # Add new entry (at beginning for newest first)
        history.insert(0, {
            'id': collage_id,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'imageCount': int(image_count),
            'layout': layout,
            'timestamp': datetime.now().timestamp()
        })
        
        # Keep only last 50
        history = history[:50]
        
        # Save history
        with open(COLLAGE_HISTORY_JSON, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
        
        return jsonify({
            'success': True,
            'id': collage_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@image_bp.route('/api/collage-history', methods=['GET'])
def get_collage_history():
    """Get list of saved collages"""
    try:
        if not os.path.exists(COLLAGE_HISTORY_JSON):
            return jsonify({'success': True, 'history': []})
        
        with open(COLLAGE_HISTORY_JSON, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@image_bp.route('/api/collage-thumbnail/<collage_id>', methods=['GET'])
def get_collage_thumbnail(collage_id):
    """Get thumbnail image for collage"""
    try:
        image_path = os.path.join(COLLAGE_HISTORY_DIR, f'{collage_id}.png')
        abs_path = os.path.abspath(image_path)
        
        print(f"[DEBUG] Thumbnail request for ID: {collage_id}")
        print(f"[DEBUG] Relative path: {image_path}")
        print(f"[DEBUG] Absolute path: {abs_path}")
        print(f"[DEBUG] File exists: {os.path.exists(abs_path)}")
        
        if not os.path.exists(abs_path):
            return jsonify({'error': 'Not found', 'path': abs_path}), 404
        
        return send_file(abs_path, mimetype='image/png')
        
    except Exception as e:
        print(f"[ERROR] Thumbnail error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@image_bp.route('/api/collage-data/<collage_id>', methods=['GET'])
def get_collage_data(collage_id):
    """Get collage data for re-editing (currently not supported)"""
    # For now, just return error since we don't store original images
    return jsonify({
        'success': False,
        'error': 'Re-editing is not supported yet'
    }), 501

@image_bp.route('/api/collage-delete/<collage_id>', methods=['DELETE'])
def delete_collage(collage_id):
    """Delete collage from history"""
    try:
        # Delete image file
        image_path = os.path.join(COLLAGE_HISTORY_DIR, f'{collage_id}.png')
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Update history JSON
        if os.path.exists(COLLAGE_HISTORY_JSON):
            with open(COLLAGE_HISTORY_JSON, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            history = [item for item in history if item['id'] != collage_id]
            
            with open(COLLAGE_HISTORY_JSON, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@image_bp.route('/api/enhance_web_image', methods=['POST'])
def enhance_web_image():
    """
    Enhance image quality using OpenCV:
    - CLAHE for local contrast
    - Sharpen + denoise
    - Detail enhancement
    """
    try:
        f = request.files.get('image')
        if not f:
            return jsonify({'success': False, 'error': 'No image provided'}), 400
        
        # Load image
        img = Image.open(f.stream).convert('RGB')
        bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # Tăng local contrast (CLAHE) - giảm clipLimit để tránh "nổ" contrast
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        l2 = clahe.apply(l)
        lab = cv2.merge([l2, a, b])
        bgr_clahe = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Sharpen nhẹ nhàng hơn - tránh halo và "cháy" ảnh
        blur = cv2.GaussianBlur(bgr_clahe, (0, 0), 1.0)
        sharp = cv2.addWeighted(bgr_clahe, 1.2, blur, -0.2, 0)
        
        # Blend mềm với ảnh gốc để giữ tự nhiên
        blended = cv2.addWeighted(bgr_clahe, 0.6, sharp, 0.4, 0)
        
        # Khử noise JPEG
        denoise = cv2.fastNlMeansDenoisingColored(blended, None, 7, 7, 7, 21)

        # Tăng chi tiết nhẹ nhàng - giảm sigma để tránh quá sắc nét
        enhanced = cv2.detailEnhance(denoise, sigma_s=10, sigma_r=0.2)
        
        # Bilateral filter cuối để ảnh mượt tự nhiên như Pixlr
        out = cv2.bilateralFilter(enhanced, d=5, sigmaColor=30, sigmaSpace=20)
        
        # Encode to PNG
        _, buf = cv2.imencode('.png', out)
        
        return (buf.tobytes(), 200, {'Content-Type': 'image/png'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@image_bp.route('/api/remove_blemish', methods=['POST'])
def remove_blemish():
    """
    Remove blemishes using OpenCV inpainting (professional healing)
    - Support both Navier-Stokes (NS) and Telea algorithms
    - Adjustable inpaint radius
    - Pre/post processing for better results
    """
    try:
        # Get image and mask
        if 'image' not in request.files or 'mask' not in request.files:
            return jsonify({'success': False, 'error': 'Image and mask required'}), 400
        
        image_file = request.files['image']
        mask_file = request.files['mask']
        
        # Get parameters
        method = request.form.get('method', 'ns')  # 'ns' or 'telea'
        radius = int(request.form.get('radius', 5))  # 3-10 range
        
        # Load image
        img = Image.open(image_file.stream).convert('RGB')
        bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Load mask (white = area to heal, black = keep)
        mask_img = Image.open(mask_file.stream).convert('L')
        mask = np.array(mask_img)
        
        # Pre-process: Bilateral filter for better edge preservation
        bgr_smooth = cv2.bilateralFilter(bgr, d=5, sigmaColor=50, sigmaSpace=50)
        
        # Dilate mask slightly for better blending
        kernel = np.ones((3,3), np.uint8)
        mask_dilated = cv2.dilate(mask, kernel, iterations=2)
        
        # Choose inpainting method
        if method == 'telea':
            # Telea: Fast Marching Method (faster, good for small areas)
            healed = cv2.inpaint(bgr_smooth, mask_dilated, inpaintRadius=radius, flags=cv2.INPAINT_TELEA)
        else:
            # Navier-Stokes: Fluid dynamics (slower, more natural for large areas)
            healed = cv2.inpaint(bgr_smooth, mask_dilated, inpaintRadius=radius, flags=cv2.INPAINT_NS)
        
        # Post-process: Edge-preserving smoothing on healed areas only
        # Create soft mask for blending
        mask_float = mask_dilated.astype(float) / 255.0
        mask_blur = cv2.GaussianBlur(mask_float, (7, 7), 0)
        mask_3ch = np.stack([mask_blur] * 3, axis=2)
        
        # Blend original with healed using soft mask
        result = (bgr * (1 - mask_3ch) + healed * mask_3ch).astype(np.uint8)
        
        # Final touch: Subtle bilateral filter on result for seamless blending
        result = cv2.bilateralFilter(result, d=3, sigmaColor=20, sigmaSpace=20)
        
        # Encode to PNG
        _, buf = cv2.imencode('.png', result)
        
        return (buf.tobytes(), 200, {'Content-Type': 'image/png'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
