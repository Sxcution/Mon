import uuid
import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, send_from_directory
from app.database import get_db_connection, DATA_DIR
from bs4 import BeautifulSoup
from PIL import Image
import io
import base64

SOUNDS_FOLDER = os.path.join(DATA_DIR, "sounds")
NOTES_IMAGES_FOLDER = os.path.join(DATA_DIR, "notes_images")

# --- BLUEPRINT DEFINITION ---
notes_bp = Blueprint("notes_feature", __name__, url_prefix="/notes")

# --- GLOBAL VARS FOR NOTES (Copied from temp_Main.pyw) ---
NOTIFICATIONS_QUEUE = []

# --- CORE FUNCTIONS (Copied from temp_Main.pyw, lines 1459-1507) ---
def check_and_queue_reminders():
    """Checks for due reminders from SQLite and queues them for notification."""
    conn = get_db_connection()
    now_utc_iso = datetime.now(timezone.utc).isoformat()
    due_notes = conn.execute(
        "SELECT * FROM notes WHERE status = 'active' AND due_time IS NOT NULL AND due_time <= ?",
        (now_utc_iso,)
    ).fetchall()

    if not due_notes:
        conn.close()
        return

    sound_files = []
    if os.path.exists(SOUNDS_FOLDER):
        sound_files = [f for f in os.listdir(SOUNDS_FOLDER) if f.endswith((".wav", ".mp3", ".ogg"))]
    
    ids_to_update = []
    for note in due_notes:
        note_dict = dict(note)
        title_lower = (note_dict.get("title_html") or "").lower() # Use title_html
        sound_url = "/notes/sounds/notification.wav" # Default
        for sf in sound_files:
            if os.path.splitext(sf)[0].lower() in title_lower:
                sound_url = f"/notes/sounds/{sf}"
                break
        
        notification_payload = {
            "id": note_dict["id"],
            "title": BeautifulSoup(note_dict["title_html"], "html.parser").get_text(),
            "notes": note_dict.get("content_html", ""),
            "sound_url": sound_url
        }
        if not any(q['id'] == note_dict['id'] for q in NOTIFICATIONS_QUEUE):
            NOTIFICATIONS_QUEUE.append(notification_payload)
        
        ids_to_update.append(note_dict["id"])

    if ids_to_update:
        # Update status in bulk
        placeholders = ','.join('?' for _ in ids_to_update)
        conn.execute(f"UPDATE notes SET status = 'notified', due_time = NULL WHERE id IN ({placeholders})", ids_to_update)
        conn.commit()
    
    conn.close()

# --- API ROUTES (Copied from temp_Main.pyw, starting from line 1509) ---
@notes_bp.route("/api/get")
def api_get_notes():
    check_and_queue_reminders()
    conn = get_db_connection()
    notes_rows = conn.execute("SELECT * FROM notes ORDER BY modified_at DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in notes_rows])

@notes_bp.route("/api/add", methods=["POST"])
def api_add_note():
    data = request.json
    title_html, content_html = data.get("title_html", "").strip(), data.get("content_html", "").strip()
    reminder_time = data.get("reminder_time") or None

    if not title_html and not content_html:
        return jsonify({"error": "Tiêu đề hoặc nội dung không được để trống"}), 400
    
    now = datetime.now(timezone.utc).isoformat()
    new_note = {
        "id": str(uuid.uuid4()), "title_html": title_html, "content_html": content_html,
        "due_time": reminder_time, 
        "status": "active" if reminder_time else "none", 
        "modified_at": now,
        "is_marked": data.get("is_marked", False) # Ensure is_marked is handled
    }

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO notes (id, title_html, content_html, due_time, status, modified_at, is_marked) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_note['id'], new_note['title_html'], new_note['content_html'], new_note['due_time'], new_note['status'], new_note['modified_at'], new_note['is_marked'])
    )
    conn.commit()
    
    # Fetch the newly created note to return complete data
    saved_note_row = conn.execute("SELECT * FROM notes WHERE id = ?", (new_note['id'],)).fetchone()
    conn.close()
    return jsonify(dict(saved_note_row)), 201

@notes_bp.route("/api/update/<note_id>", methods=["POST"])
def api_update_note(note_id):
    data = request.json
    title_html, content_html = data.get("title_html", "").strip(), data.get("content_html", "").strip()
    reminder_time = data.get("reminder_time") # Allows setting reminder to null

    if not title_html and not content_html:
        return jsonify({"error": "Tiêu đề hoặc nội dung không được để trống"}), 400
    
    modified_at = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection()
    
    # Get current status to avoid overwriting 'notified'
    current_note = conn.execute("SELECT status FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not current_note:
        conn.close()
        return jsonify({"error": "Không tìm thấy ghi chú"}), 404

    # Determine the new status
    if reminder_time:
        status = "active"
    elif current_note['status'] == 'active':
        status = 'none'
    else: # Keep 'notified' or other statuses if they exist
        status = current_note['status']

    cursor = conn.execute(
        "UPDATE notes SET title_html = ?, content_html = ?, due_time = ?, status = ?, modified_at = ? WHERE id = ?",
        (title_html, content_html, reminder_time, status, modified_at, note_id)
    )
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Không tìm thấy ghi chú"}), 404
    
    updated_note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return jsonify(dict(updated_note))

@notes_bp.route("/api/delete/<note_id>", methods=["POST"])
def api_delete_note(note_id):
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True}) if cursor.rowcount > 0 else (jsonify({"error": "Không tìm thấy ghi chú"}), 404)

@notes_bp.route("/api/mark/<note_id>", methods=["POST"])
def api_toggle_mark(note_id):
    conn = get_db_connection()
    note = conn.execute("SELECT is_marked FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        conn.close()
        return jsonify({"error": "Không tìm thấy ghi chú"}), 404
    
    new_marked_state = not note["is_marked"]
    conn.execute("UPDATE notes SET is_marked = ? WHERE id = ?", (new_marked_state, note_id))
    conn.commit()
    
    updated_note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return jsonify(dict(updated_note))

@notes_bp.route("/api/acknowledge-notification/<note_id>", methods=["POST"])
def acknowledge_notification(note_id):
    conn = get_db_connection()
    conn.execute("UPDATE notes SET status = 'notified', due_time = NULL WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@notes_bp.route("/api/check-notifications")
def api_check_notifications():
    """Endpoint để frontend kiểm tra xem có thông báo mới không."""
    check_and_queue_reminders()
    if NOTIFICATIONS_QUEUE:
        # Lấy thông báo đầu tiên và xóa khỏi hàng đợi
        notification_to_send = NOTIFICATIONS_QUEUE.pop(0)
        return jsonify(notification_to_send)
    return jsonify(None) # Trả về null nếu không có gì

@notes_bp.route("/sounds/<path:filename>")
def serve_sound(filename):
    return send_from_directory(os.path.join(DATA_DIR, "sounds"), filename)

@notes_bp.route("/api/upload-image", methods=["POST"])
def api_upload_image():
    """Upload image for profile, resize to max 1024px width, return URL"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        # Create notes_images folder if not exists
        os.makedirs(NOTES_IMAGES_FOLDER, exist_ok=True)
        
        # Generate unique filename
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            ext = '.png'
        
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(NOTES_IMAGES_FOLDER, unique_filename)
        
        # Open and resize image
        img = Image.open(file.stream)
        
        # Resize if width > 1024px
        if img.width > 1024:
            ratio = 1024 / img.width
            new_height = int(img.height * ratio)
            img = img.resize((1024, new_height), Image.Resampling.LANCZOS)
        
        # Save image
        img.save(file_path, optimize=True, quality=85)
        
        # Return URL
        image_url = f"/notes/images/{unique_filename}"
        return jsonify({"success": True, "url": image_url}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notes_bp.route("/images/<path:filename>")
def serve_note_image(filename):
    """Serve uploaded note images"""
    return send_from_directory(NOTES_IMAGES_FOLDER, filename)
