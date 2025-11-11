import os
import threading
import webbrowser
import time
from PIL import Image, ImageDraw, ImageFont
from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem as TrayMenuItem
import json

# Internal module imports
from app import create_app
from app.database import init_database
# Import the settings loader directly
from app.settings_routes import load_dashboard_settings, DASHBOARD_SETTINGS_FILE 

# --- GLOBAL CONFIGURATION ---
HOST = "0.0.0.0"
PORT = 5000
BASE_URL = f"http://127.0.0.1:5000"
APP_NAME = "MonDashboard"

# --- APPLICATION INSTANCE ---
app = create_app()

# --- HELPER FUNCTIONS ---

def get_settings():
    """Tries to load settings, falls back to default empty dict if file not found."""
    try:
        return load_dashboard_settings()
    except FileNotFoundError:
        # CRITICAL: Create default file if it doesn't exist on first run
        default_settings = {'auto_start': False, 'auto_open_dashboard': True, 'mxh_refresh_interval': 15000}
        os.makedirs(os.path.dirname(DASHBOARD_SETTINGS_FILE), exist_ok=True)
        try:
            with open(DASHBOARD_SETTINGS_FILE, 'w') as f:
                json.dump(default_settings, f, indent=2)
        except Exception as e:
            print(f"WARNING: Could not write default settings file: {e}")
        return default_settings
    except json.JSONDecodeError:
        print("WARNING: Corrupted settings file. Using defaults.")
        return {'auto_start': False, 'auto_open_dashboard': True, 'mxh_refresh_interval': 15000}

def open_dashboard_in_browser(icon=None, item=None):
    """Opens the dashboard in the default web browser."""
    # Give the Flask server a moment to start up completely
    time.sleep(0.5)
    webbrowser.open_new_tab(BASE_URL)

def exit_application(icon, item):
    """Stops the system tray icon and closes the application."""
    # NOTE: This only stops the tray icon; the Flask thread is daemonized and 
    # will stop when the main script terminates (which happens after icon.stop())
    icon.stop()
    print(f"[{APP_NAME}] Shutting down from system tray...")

def create_tray_icon(is_first_run):
    """Creates the system tray icon with a simple generated icon."""
    try:
        # Create a simple 'S' icon (64x64) as a placeholder
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color='#2c303a')
        draw = ImageDraw.Draw(image)
        try:
             # Use a generic font (PIL will handle loading system font)
            font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default() 
        draw.text((10, 10), "S", fill="#0d6efd", font=font)
    except Exception as e:
        print(f"Error creating icon: {e}. Using a fallback.")
        image = Image.new('RGB', (64, 64), color='#2c303a')

    # Define the menu structure
    menu = TrayMenu(
        # Double-click handler is enabled by default=True
        TrayMenuItem(f"Open {APP_NAME} Dashboard", open_dashboard_in_browser, default=True),
        TrayMenuItem("Exit", exit_application)
    )

    # Create the icon object
    icon = TrayIcon(APP_NAME, image, APP_NAME, menu)
    return icon

def run_server():
    """Runs the Flask server in the current thread."""
    try:
        # Only initialize DB if it's the main process (not a reloader instance)
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            print(f"[{APP_NAME}] Initializing database...")
            init_database()
            print(f"[{APP_NAME}] Starting Flask server on {BASE_URL} (Thread: {threading.current_thread().name})")
        
        # use_reloader=False is CRITICAL for multi-threading stability
        # Set Flask logger to WARNING to reduce spam logs
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)
        
        app.run(host=HOST, port=PORT, debug=True, use_reloader=False) 

    except Exception as e:
        print(f"[{APP_NAME}] Flask server error: {e}")

# --- MAIN EXECUTION ---

def main():
    """Main function to start server thread and run system tray."""
    is_first_run = not os.path.exists(DASHBOARD_SETTINGS_FILE)
    
    # 1. Start the Flask server in a separate daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True, name="FlaskServerThread")
    server_thread.start()
    
    # Wait briefly for the server thread to start
    time.sleep(1) 
    
    # 2. Check settings and open browser if configured
    settings = get_settings()
    if settings.get("auto_open_dashboard", True):
        open_dashboard_in_browser() 
        
    # 3. Run the System Tray Icon
    icon = create_tray_icon(is_first_run)
    print(f"[{APP_NAME}] Running in system tray. Double-click icon or right-click > Open Dashboard.")
    icon.run()

if __name__ == "__main__":
    # CRITICAL: Set working directory to project root for resource/data access
    try:
        # os.path.dirname(os.path.abspath(__file__)) points to the directory containing run.pyw
        app_root = os.path.dirname(os.path.abspath(__file__))
        if os.getcwd() != app_root:
            os.chdir(app_root)
        print(f"[{APP_NAME}] Working Directory set to: {os.getcwd()}")
    except Exception as e:
        print(f"[{APP_NAME}] WARNING: Could not set working directory: {e}")

    main()
