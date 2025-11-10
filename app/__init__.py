from flask import Flask
import os


def create_app():
    """
    Hàm khởi tạo và cấu hình ứng dụng Flask.
    """
    app = Flask(__name__)
    
    # Thiết lập một secret key cho ứng dụng
    app.config['SECRET_KEY'] = 'your_super_secret_key_for_flask_app'
    
    # Set UPLOAD_FOLDER (match Main.pyw line 62-66)
    APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(APP_ROOT, "data")
    UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploaded_sessions")
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # 🔍 Initialize database (match Main.pyw)
    with app.app_context():
        from . import database
        database.ensure_database()
    
    # Đăng ký các routes từ file routes.py
    with app.app_context():
        from . import routes
        from . import notes_routes
        from . import mxh_routes
        from . import mxh_api
        from . import settings_routes
        from . import image_routes
        from . import telegram_routes
        from . import automatic_routes
        app.register_blueprint(notes_routes.notes_bp)
        app.register_blueprint(mxh_routes.mxh_bp)
        app.register_blueprint(mxh_api.mxh_api_bp)
        app.register_blueprint(settings_routes.settings_bp)
        app.register_blueprint(image_routes.image_bp)
        app.register_blueprint(telegram_routes.telegram_bp)
        app.register_blueprint(automatic_routes.automatic_bp)
    
    return app
