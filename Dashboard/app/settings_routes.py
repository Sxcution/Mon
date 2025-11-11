"""
Settings Dashboard Routes
Quản lý cài đặt dashboard với real-time updates
"""
from flask import Blueprint, render_template, request, jsonify
import os
import json
import platform  # New Import
import subprocess  # New Import
import sys # New Import

# Conditional import for Windows Registry
try:
    if platform.system() == 'Windows':
        import winreg
except ImportError:
    pass  # winreg is not available on non-Windows systems

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# Path to dashboard settings file
DASHBOARD_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'dashboard_settings.json')

def load_dashboard_settings():
    """Load dashboard settings from JSON file."""
    if os.path.exists(DASHBOARD_SETTINGS_FILE):
        with open(DASHBOARD_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            # Ensure the new setting exists in loaded data, default to 15 seconds (15000 ms)
            if 'mxh_refresh_interval' not in settings:
                settings['mxh_refresh_interval'] = 15000
            return settings
    return {
        'auto_start': False, 
        'auto_open_dashboard': True,
        'shutdown_timer': {'enabled': False, 'hours': 0, 'minutes': 0},
        'notification_timer': {'enabled': False, 'hours': 0, 'minutes': 0, 'message': ''},
        'mxh_refresh_interval': 15000  # Default 15000 ms (15 seconds)
    }

def save_dashboard_settings(settings):
    """Save dashboard settings to JSON file."""
    os.makedirs(os.path.dirname(DASHBOARD_SETTINGS_FILE), exist_ok=True)
    with open(DASHBOARD_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

# NEW FUNCTION: Handle OS-level auto-start configuration (Windows-centric)
def handle_auto_start_os_config(enabled):
    """Creates or removes shortcut in Windows Startup folder (simple and effective)."""
    if platform.system() != 'Windows':
        print("Auto-start feature is only implemented for Windows.")
        return

    try:
        # Get the absolute path to run.pyw
        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        run_pyw_path = os.path.join(app_root, "run.pyw")
        
        if not os.path.exists(run_pyw_path):
            raise Exception(f"run.pyw not found at {run_pyw_path}")
        
        # Windows Startup folder path
        startup_path = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        shortcut_path = os.path.join(startup_path, "MonDashboard.lnk")
        
        if enabled:
            # Create startup folder if it doesn't exist
            os.makedirs(startup_path, exist_ok=True)
            
            # Create shortcut using PowerShell (simple and reliable)
            ps_command = f'''
            $WshShell = New-Object -ComObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{run_pyw_path}"
            $Shortcut.WorkingDirectory = "{app_root}"
            $Shortcut.Description = "MonDashboard - Khởi động cùng Windows"
            $Shortcut.WindowStyle = 7
            $Shortcut.Save()
            '''
            
            # Execute PowerShell command
            result = subprocess.run([
                'powershell', '-Command', ps_command
            ], capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                print(f"[SUCCESS] Created startup shortcut: {shortcut_path}")
            else:
                raise Exception(f"PowerShell error: {result.stderr}")
        else:
            # Remove shortcut if it exists
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                print(f"[SUCCESS] Removed startup shortcut: {shortcut_path}")
            else:
                print("[INFO] Startup shortcut not found (already removed)")
                
    except Exception as e:
        print(f"[ERROR] Error configuring Windows startup: {e}")
        raise e

# ===== PAGE ROUTES =====
@settings_bp.route('/')
def settings_page():
    """Render settings page."""
    return render_template('settings.html', title='Cài Đặt Dashboard')

# ===== API ROUTES =====
@settings_bp.route('/api/settings', methods=['GET'])
def get_settings():
    """Get all dashboard settings."""
    try:
        settings = load_dashboard_settings()
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/settings', methods=['POST'])
def update_settings():
    """Update dashboard settings."""
    try:
        data = request.get_json()
        settings = load_dashboard_settings()
        settings.update(data)
        save_dashboard_settings(settings)
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/settings/auto-start', methods=['PUT'])
def toggle_auto_start():
    """Toggle auto-start setting and configure OS startup."""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)  # Capture state here
        settings = load_dashboard_settings()
        
        # 1. Update OS configuration (CRITICAL FIX)
        handle_auto_start_os_config(enabled) 
        
        # 2. Save setting to JSON
        settings['auto_start'] = enabled
        save_dashboard_settings(settings)
        
        return jsonify({'success': True, 'auto_start': settings['auto_start']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/settings/auto-open-dashboard', methods=['PUT'])
def toggle_auto_open_dashboard():
    """Toggle auto-open dashboard setting."""
    try:
        data = request.get_json()
        settings = load_dashboard_settings()
        settings['auto_open_dashboard'] = data.get('enabled', False)
        save_dashboard_settings(settings)
        return jsonify({'success': True, 'auto_open_dashboard': settings['auto_open_dashboard']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/settings/shutdown-timer', methods=['PUT'])
def update_shutdown_timer():
    """Update shutdown timer settings."""
    try:
        data = request.get_json()
        settings = load_dashboard_settings()
        settings['shutdown_timer'] = {
            'enabled': data.get('enabled', False),
            'hours': data.get('hours', 0),
            'minutes': data.get('minutes', 0)
        }
        save_dashboard_settings(settings)
        return jsonify({'success': True, 'shutdown_timer': settings['shutdown_timer']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/settings/notification-timer', methods=['PUT'])
def update_notification_timer():
    """Update notification timer settings."""
    try:
        data = request.get_json()
        settings = load_dashboard_settings()
        settings['notification_timer'] = {
            'enabled': data.get('enabled', False),
            'hours': data.get('hours', 0),
            'minutes': data.get('minutes', 0),
            'message': data.get('message', '')
        }
        save_dashboard_settings(settings)
        return jsonify({'success': True, 'notification_timer': settings['notification_timer']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/settings/mxh-refresh-interval', methods=['PUT'])
def update_mxh_refresh_interval():
    """Update MXH dashboard auto-refresh interval (in milliseconds)."""
    try:
        data = request.get_json()
        interval = data.get('interval_ms')  # Expecting milliseconds, e.g., 15000
        if not isinstance(interval, int) or interval < 3000:  # Enforce minimum 3 seconds (3000ms)
            return jsonify({'error': 'Interval must be an integer >= 3000ms'}), 400
            
        settings = load_dashboard_settings()
        settings['mxh_refresh_interval'] = interval
        save_dashboard_settings(settings)
        return jsonify({'success': True, 'mxh_refresh_interval': settings['mxh_refresh_interval']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/system/shutdown', methods=['POST'])
def system_shutdown():
    """Shutdown system (Windows only)."""
    try:
        import platform
        if platform.system() == 'Windows':
            import subprocess
            subprocess.Popen(['shutdown', '/s', '/t', '0'])
            return jsonify({'success': True, 'message': 'Shutting down...'})
        else:
            return jsonify({'error': 'Only supported on Windows'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
