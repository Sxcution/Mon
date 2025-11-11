#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AHK Manager - GUI Application for Managing AutoHotkey Scripts
Author: Mon
Version: 1.0.0
"""

import sys
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QMessageBox, QGroupBox, QCheckBox,
    QTabWidget, QHeaderView, QFileDialog, QSplitter, QDialog, QDialogButtonBox,
    QShortcut, QStyledItemDelegate
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QProcess, QEvent, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QKeySequence


class NoSelectDelegate(QStyledItemDelegate):
    """Delegate để bỏ select all khi edit cell"""
    
    def createEditor(self, parent, option, index):
        """Tạo editor và thiết lập không select all"""
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            # Kết nối signal để bỏ select all khi editor hiển thị
            QTimer.singleShot(0, lambda: self._deselect_text(editor))
        return editor
    
    def _deselect_text(self, editor):
        """Bỏ select và đặt cursor ở cuối"""
        if editor and isinstance(editor, QLineEdit):
            editor.deselect()
            editor.setCursorPosition(len(editor.text()))
    
    def setEditorData(self, editor, index):
        """Override để không select all"""
        super().setEditorData(editor, index)
        if isinstance(editor, QLineEdit):
            # Move cursor to end instead of selecting all
            editor.deselect()
            editor.setCursorPosition(len(editor.text()))


class NoScrollComboBox(QComboBox):
    """ComboBox vô hiệu hóa scroll wheel"""
    
    def wheelEvent(self, event):
        """Ignore wheel events"""
        event.ignore()


class HotkeyCellWidget(QLineEdit):
    """Widget trong table cell để capture hotkey"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_hotkey = ""
        self.display_hotkey = ""
        self.textChanged.connect(self.on_text_changed)
    
    def on_text_changed(self, text):
        """Khi text thay đổi, check xem có phải hotkey modifier không"""
        # Nếu text chứa ^, !, +, # thì convert sang display format
        if any(c in text for c in ['^', '!', '+', '#']):
            self.display_hotkey = self.ahk_to_display(text)
            self.raw_hotkey = text
            # Block signals để tránh loop
            self.blockSignals(True)
            self.setText(self.display_hotkey)
            self.blockSignals(False)
    
    def keyPressEvent(self, event):
        """Capture hotkey khi nhấn phím"""
        key = event.key()
        modifiers = event.modifiers()
        
        # Ignore just modifier keys
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return
        
        # Check if có modifier
        has_modifier = modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier)
        
        if has_modifier:
            # Build AHK format
            ahk_parts = []
            display_parts = []
            
            if modifiers & Qt.ControlModifier:
                ahk_parts.append('^')
                display_parts.append('Ctrl')
            if modifiers & Qt.AltModifier:
                ahk_parts.append('!')
                display_parts.append('Alt')
            if modifiers & Qt.ShiftModifier:
                ahk_parts.append('+')
                display_parts.append('Shift')
            if modifiers & Qt.MetaModifier:
                ahk_parts.append('#')
                display_parts.append('Win')
            
            # Key name
            key_name = self.get_key_name(key)
            if key_name:
                ahk_parts.append(key_name)
                display_parts.append(key_name)
                
                self.raw_hotkey = ''.join(ahk_parts)
                self.display_hotkey = '+'.join(display_parts)
                
                # Block signals và set text
                self.blockSignals(True)
                self.setText(self.display_hotkey)
                self.blockSignals(False)
        else:
            # Không có modifier, cho phép gõ text bình thường (hotstring)
            super().keyPressEvent(event)
    
    def get_key_name(self, key):
        """Convert Qt key to AHK key name"""
        if Qt.Key_0 <= key <= Qt.Key_9:
            return chr(key)
        if Qt.Key_A <= key <= Qt.Key_Z:
            return chr(key).lower()
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            return f"F{key - Qt.Key_F1 + 1}"
        
        special_keys = {
            Qt.Key_Space: 'Space',
            Qt.Key_Enter: 'Enter',
            Qt.Key_Return: 'Enter',
            Qt.Key_Tab: 'Tab',
            Qt.Key_Escape: 'Escape',
            Qt.Key_Backspace: 'Backspace',
            Qt.Key_Delete: 'Delete',
            Qt.Key_Insert: 'Insert',
            Qt.Key_Home: 'Home',
            Qt.Key_End: 'End',
            Qt.Key_PageUp: 'PgUp',
            Qt.Key_PageDown: 'PgDn',
            Qt.Key_Up: 'Up',
            Qt.Key_Down: 'Down',
            Qt.Key_Left: 'Left',
            Qt.Key_Right: 'Right',
        }
        return special_keys.get(key, '')
    
    def ahk_to_display(self, ahk_hotkey):
        """Convert AHK format to display format"""
        if not ahk_hotkey:
            return ""
        
        parts = []
        i = 0
        while i < len(ahk_hotkey):
            char = ahk_hotkey[i]
            if char == '^':
                parts.append('Ctrl')
            elif char == '!':
                parts.append('Alt')
            elif char == '+':
                parts.append('Shift')
            elif char == '#':
                parts.append('Win')
            else:
                parts.append(ahk_hotkey[i:])
                break
            i += 1
        
        return '+'.join(parts) if parts else ahk_hotkey
    
    def get_raw_hotkey(self):
        """Get raw AHK format hotkey"""
        # Nếu có raw_hotkey thì return, không thì return text
        return self.raw_hotkey if self.raw_hotkey else self.text()
    
    def focusInEvent(self, event):
        """Khi focus, KHÔNG select all"""
        super().focusInEvent(event)
        # Move cursor to end instead of selecting all
        self.deselect()
        self.setCursorPosition(len(self.text()))


class HotkeyCapture(QLineEdit):
    """Widget để capture hotkey từ keyboard"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Click và nhấn phím...")
        self.setReadOnly(True)
        self.raw_hotkey = ""  # Lưu dạng AHK (^1, !a, +^s)
        self.display_hotkey = ""  # Lưu dạng hiển thị (Ctrl+1, Alt+A, Shift+Ctrl+S)
        
    def keyPressEvent(self, event):
        """Capture key press"""
        key = event.key()
        modifiers = event.modifiers()
        
        # Ignore just modifier keys
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return
        
        # Build AHK format
        ahk_parts = []
        display_parts = []
        
        # Modifiers
        if modifiers & Qt.ControlModifier:
            ahk_parts.append('^')
            display_parts.append('Ctrl')
        if modifiers & Qt.AltModifier:
            ahk_parts.append('!')
            display_parts.append('Alt')
        if modifiers & Qt.ShiftModifier:
            ahk_parts.append('+')
            display_parts.append('Shift')
        if modifiers & Qt.MetaModifier:
            ahk_parts.append('#')
            display_parts.append('Win')
        
        # Key name
        key_name = self.get_key_name(key)
        if key_name:
            ahk_parts.append(key_name)
            display_parts.append(key_name)
            
            self.raw_hotkey = ''.join(ahk_parts)
            self.display_hotkey = '+'.join(display_parts)
            self.setText(self.display_hotkey)
    
    def get_key_name(self, key):
        """Convert Qt key to AHK key name"""
        # Numbers
        if Qt.Key_0 <= key <= Qt.Key_9:
            return chr(key)
        
        # Letters
        if Qt.Key_A <= key <= Qt.Key_Z:
            return chr(key).lower()
        
        # Function keys
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            return f"F{key - Qt.Key_F1 + 1}"
        
        # Numpad
        if Qt.Key_0 <= key <= Qt.Key_9:
            if key >= 0x01000030:  # Numpad range
                return f"Numpad{key - 0x01000030}"
        
        # Special keys mapping
        special_keys = {
            Qt.Key_Space: 'Space',
            Qt.Key_Enter: 'Enter',
            Qt.Key_Return: 'Enter',
            Qt.Key_Tab: 'Tab',
            Qt.Key_Escape: 'Escape',
            Qt.Key_Backspace: 'Backspace',
            Qt.Key_Delete: 'Delete',
            Qt.Key_Insert: 'Insert',
            Qt.Key_Home: 'Home',
            Qt.Key_End: 'End',
            Qt.Key_PageUp: 'PgUp',
            Qt.Key_PageDown: 'PgDn',
            Qt.Key_Up: 'Up',
            Qt.Key_Down: 'Down',
            Qt.Key_Left: 'Left',
            Qt.Key_Right: 'Right',
        }
        
        return special_keys.get(key, '')
    
    def set_hotkey(self, ahk_hotkey):
        """Set hotkey từ string AHK format"""
        self.raw_hotkey = ahk_hotkey
        self.display_hotkey = self.ahk_to_display(ahk_hotkey)
        self.setText(self.display_hotkey)
    
    def ahk_to_display(self, ahk_hotkey):
        """Convert AHK format (^1) to display format (Ctrl+1)"""
        if not ahk_hotkey:
            return ""
        
        parts = []
        i = 0
        while i < len(ahk_hotkey):
            char = ahk_hotkey[i]
            if char == '^':
                parts.append('Ctrl')
            elif char == '!':
                parts.append('Alt')
            elif char == '+':
                parts.append('Shift')
            elif char == '#':
                parts.append('Win')
            elif char == '<':
                parts.append('Left')
            elif char == '>':
                parts.append('Right')
            else:
                # Rest is the key
                parts.append(ahk_hotkey[i:])
                break
            i += 1
        
        return '+'.join(parts)
    
    def get_raw_hotkey(self):
        """Get raw AHK format"""
        return self.raw_hotkey
    
    def mousePressEvent(self, event):
        """Focus when clicked"""
        super().mousePressEvent(event)
        self.setStyleSheet("border: 2px solid #4CAF50;")
    
    def focusOutEvent(self, event):
        """Remove border when focus lost"""
        super().focusOutEvent(event)
        self.setStyleSheet("")


class HotkeyItem:
    """Đại diện cho một hotkey/hotstring"""
    def __init__(self, trigger: str, output_type: str, output_value: str, 
                 delay: int = 100, enabled: bool = True, description: str = ""):
        self.trigger = trigger
        self.output_type = output_type  # Send, SendInput, SendEvent, Delay
        self.output_value = output_value
        self.delay = delay
        self.enabled = enabled
        self.description = description
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            'trigger': self.trigger,
            'output_type': self.output_type,
            'output_value': self.output_value,
            'delay': self.delay,
            'enabled': self.enabled,
            'description': self.description,
            'created_at': self.created_at
        }

    @staticmethod
    def from_dict(data: Dict) -> 'HotkeyItem':
        item = HotkeyItem(
            trigger=data.get('trigger', ''),
            output_type=data.get('output_type', 'SendInput'),
            output_value=data.get('output_value', ''),
            delay=data.get('delay', 100),
            enabled=data.get('enabled', True),
            description=data.get('description', '')
        )
        item.created_at = data.get('created_at', datetime.now().isoformat())
        return item

    def to_ahk_code(self) -> str:
        """Chuyển đổi thành code AHK"""
        # ExcludeApp không tạo hotkey code, chỉ dùng cho #IfWinNotActive
        if self.output_type == "ExcludeApp":
            return ""
        
        if not self.enabled:
            return f"; [DISABLED] {self.trigger}\n"
        
        lines = []
        
        # Thêm comment nếu có description
        if self.description:
            lines.append(f"; {self.description}")
        
        # Xác định loại trigger
        if self.trigger.startswith('^') or self.trigger.startswith('!') or \
           self.trigger.startswith('+') or self.trigger.startswith('#'):
            # Hotkey (Ctrl, Alt, Shift, Win)
            lines.append(f"{self.trigger}::")
        else:
            # Hotstring
            lines.append(f"::{self.trigger}::")
        
        # Output
        if self.output_type == "Send":
            lines.append(f"SendMode Input")
            lines.append(f"Send, {self.output_value}")
        elif self.output_type == "SendInput":
            lines.append(f"Sendinput {self.output_value}")
        elif self.output_type == "SendEvent":
            lines.append(f"SendEvent {self.output_value}")
        elif self.output_type == "SendRaw":
            lines.append(f"SendRaw {self.output_value}")
        elif self.output_type == "Delay":
            lines.append(f"Sleep {self.output_value}")
        elif self.output_type == "Clipboard":
            lines.append(f"ClipSaved := ClipboardAll")
            lines.append(f'Clipboard := "{self.output_value}"')
            lines.append(f"Send, ^v")
            lines.append(f"Sleep, {self.delay}")
            lines.append(f"Clipboard := ClipSaved")
            lines.append(f'ClipSaved := ""')
        
        # Delay
        if self.output_type != "Delay" and self.output_type != "Clipboard":
            lines.append(f"sleep {self.delay}")
        
        lines.append("return")
        lines.append("")  # Empty line
        
        return "\n".join(lines)


class AHKScriptManager:
    """Quản lý các script AHK"""
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            self.config_dir = Path.home() / ".ahk_manager"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "hotkeys.json"
        self.session_file = self.config_dir / "session.json"  # Lưu đường dẫn file cuối cùng
        self.hotkeys: List[HotkeyItem] = []
        self.ahk_process: Optional[QProcess] = None
        
    def load_hotkeys(self) -> List[HotkeyItem]:
        """Load danh sách hotkey từ file JSON"""
        if not self.config_file.exists():
            return []
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.hotkeys = [HotkeyItem.from_dict(item) for item in data]
                return self.hotkeys
        except Exception as e:
            print(f"🔍 Error loading hotkeys: {e}")
            return []
    
    def save_hotkeys(self, hotkeys: List[HotkeyItem]) -> bool:
        """Lưu danh sách hotkey vào file JSON"""
        try:
            data = [item.to_dict() for item in hotkeys]
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.hotkeys = hotkeys
            return True
        except Exception as e:
            print(f"🔍 Error saving hotkeys: {e}")
            return False
    
    def save_session(self, opened_file: str = None) -> bool:
        """Lưu thông tin session (file đang mở)"""
        try:
            data = {
                "opened_file": opened_file,
                "last_modified": datetime.now().isoformat()
            }
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"🔍 Error saving session: {e}")
            return False
    
    def load_session(self) -> Dict:
        """Load thông tin session"""
        if not self.session_file.exists():
            return {"opened_file": None}
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"🔍 Error loading session: {e}")
            return {"opened_file": None}
    
    def generate_ahk_script(self, hotkeys: List[HotkeyItem], 
                           output_path: str,
                           exclude_app: str = "dnplayer.exe",
                           run_as_admin: bool = True) -> bool:
        """Tạo file AHK từ danh sách hotkey"""
        try:
            lines = [
                "#SingleInstance Force",
                "#Persistent",
                "; =====================================================================",
                f"; Auto-generated by AHK Manager - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "; =====================================================================",
                ""
            ]
            
            # Parse exclude_app - có thể là nhiều app cách nhau bởi space
            exclude_apps = []
            if exclude_app:
                exclude_apps = [app.strip() for app in exclude_app.split() if app.strip()]
            
            # Exclude applications
            if exclude_apps:
                for app in exclude_apps:
                    lines.append(f"#IfWinNotActive ahk_exe {app}")
            
            # Run as admin
            if run_as_admin:
                lines.extend([
                    "if not A_IsAdmin",
                    "{",
                    '   Run *RunAs "%A_ScriptFullPath%"  ; Bắt buộc chạy lại bằng quyền Admin',
                    "   ExitApp",
                    "}",
                    ""
                ])
            
            # Generate hotkey code
            for hotkey in hotkeys:
                lines.append(hotkey.to_ahk_code())
            
            # End condition
            if exclude_apps:
                lines.append("#IfWinActive")
            
            # Write to file với UTF-8 BOM để tránh lỗi font tiếng Việt
            with open(output_path, 'w', encoding='utf-8-sig') as f:
                f.write("\n".join(lines))
            
            print(f"🔍 Generated AHK script: {output_path} (UTF-8 BOM)")
            return True
            
        except Exception as e:
            print(f"🔍 Error generating AHK script: {e}")
            return False


class AHKManagerGUI(QMainWindow):
    """GUI chính của AHK Manager"""
    
    def __init__(self):
        super().__init__()
        self.manager = AHKScriptManager()
        self.ahk_process = None
        self.current_ahk_file = str(Path.home() / "Desktop" / "Mon" / "AHK_Generated.ahk")
        self.opened_ahk_file = None  # Track file đang mở
        
        self.init_ui()
        
        # Khôi phục session (file đã mở lần trước)
        # Chỉ load data nếu file session còn tồn tại
        self.restore_session()
    
    def apply_dark_theme(self):
        """Apply dark theme to application"""
        app = QApplication.instance()
        
        # Dark palette
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
        
        app.setPalette(dark_palette)
        
        # Additional stylesheet
        app.setStyleSheet("""
            QToolTip { 
                color: #ffffff; 
                background-color: #2a2a2a; 
                border: 1px solid #555;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 5px 15px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 1px solid #777;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666;
            }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #2a82da;
            }
            QTableWidget {
                background-color: #2a2a2a;
                gridline-color: #555;
                border: 1px solid #555;
            }
            QTableWidget::item:selected {
                background-color: #2a82da;
            }
            QHeaderView::section {
                background-color: #3a3a3a;
                border: 1px solid #555;
                padding: 4px;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #555;
            }
            QTabBar::tab {
                background-color: #3a3a3a;
                border: 1px solid #555;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4a4a4a;
                border-bottom: 2px solid #2a82da;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #555;
                background-color: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #2a82da;
                background-color: #2a82da;
            }
            QStatusBar {
                background-color: #3a3a3a;
                color: #ccc;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #3a3a3a;
                selection-color: #2a82da;
            }
            QComboBox QAbstractItemView::item {
                color: white;
                background-color: #2a2a2a;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item:hover {
                color: #2a82da;
                background-color: #3a3a3a;
            }
            QComboBox QAbstractItemView::item:selected {
                color: #2a82da;
                background-color: #3a3a3a;
            }
        """)
        
    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("AHK Manager - AutoHotkey Script Generator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Apply dark theme
        self.apply_dark_theme()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Tab 1: Quản lý Hotkeys
        tab1 = self.create_hotkey_tab()
        tab_widget.addTab(tab1, "📝 Quản lý Hotkeys")
        
        # Tab 2: Cài đặt
        tab2 = self.create_settings_tab()
        tab_widget.addTab(tab2, "🔧 Cài đặt")
        
        # Status bar
        self.statusBar().showMessage("Sẵn sàng")
        
    def create_hotkey_tab(self) -> QWidget:
        """Tab quản lý hotkeys"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # === Chỉ giữ lại bảng danh sách hotkeys ===
        table_group = QGroupBox("Danh sách Hotkeys")
        table_layout = QVBoxLayout()
        
        self.hotkey_table = QTableWidget()
        self.hotkey_table.setColumnCount(6)
        self.hotkey_table.setHorizontalHeaderLabels([
            "Phím tắt", "Loại", "Output", "Delay", "Trạng thái", "Mô tả"
        ])
        self.hotkey_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.hotkey_table.setSelectionBehavior(QTableWidget.SelectItems)  # Chỉ select từng ô, không cả hàng
        self.hotkey_table.setSelectionMode(QTableWidget.SingleSelection)
        self.hotkey_table.setFocusPolicy(Qt.StrongFocus)
        
        # TẮT HOÀN TOÀN selection highlight
        # Set custom palette to disable selection color
        palette = self.hotkey_table.palette()
        palette.setColor(QPalette.Highlight, QColor("#2a2a2a"))  # Same as background
        palette.setColor(QPalette.HighlightedText, QColor("white"))  # Keep white text
        self.hotkey_table.setPalette(palette)
        
        # Override stylesheet - Viền xanh khi select
        self.hotkey_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                gridline-color: #555;
                border: 1px solid #555;
                selection-background-color: #2a2a2a;
                selection-color: white;
            }
            QTableWidget::item {
                background-color: #2a2a2a;
                color: white;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #2a82da;
            }
            QTableWidget::item:focus {
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #2a82da;
            }
        """)
        # Single click to edit, không select all
        self.hotkey_table.setEditTriggers(
            QTableWidget.CurrentChanged |  # Single click
            QTableWidget.SelectedClicked |
            QTableWidget.EditKeyPressed | 
            QTableWidget.AnyKeyPressed
        )
        self.hotkey_table.itemChanged.connect(self.on_table_item_changed)
        
        # Set delegate để bỏ select all
        delegate = NoSelectDelegate(self.hotkey_table)
        self.hotkey_table.setItemDelegate(delegate)
        
        table_layout.addWidget(self.hotkey_table)
        
        # Table buttons
        table_btn_layout = QHBoxLayout()
        
        self.add_row_btn = QPushButton("➕ Thêm Hotkey")
        self.add_row_btn.clicked.connect(self.add_empty_row)
        table_btn_layout.addWidget(self.add_row_btn)
        
        self.delete_btn = QPushButton("🗑️ Xóa đã chọn")
        self.delete_btn.clicked.connect(self.delete_hotkey)
        table_btn_layout.addWidget(self.delete_btn)
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_changes)
        table_btn_layout.addWidget(self.save_btn)
        
        self.save_as_btn = QPushButton("💾 Save as AHK")
        self.save_as_btn.clicked.connect(self.save_as_ahk)
        table_btn_layout.addWidget(self.save_as_btn)
        
        self.open_btn = QPushButton("📂 Open AHK")
        self.open_btn.clicked.connect(self.open_ahk_file)
        table_btn_layout.addWidget(self.open_btn)
        
        table_btn_layout.addStretch()
        table_layout.addLayout(table_btn_layout)
        
        # Current file path label
        self.current_file_label = QLabel("📄 File: <i>Chưa mở file nào</i>")
        self.current_file_label.setStyleSheet("color: #999; font-size: 11px; padding: 5px;")
        self.current_file_label.setWordWrap(True)
        table_layout.addWidget(self.current_file_label)
        
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        return tab
    
    def create_settings_tab(self) -> QWidget:
        """Tab cài đặt"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        settings_group = QGroupBox("Cài đặt chung")
        settings_layout = QVBoxLayout()
        
        # Run as admin
        self.run_as_admin_cb = QCheckBox("Chạy AHK với quyền Admin")
        self.run_as_admin_cb.setChecked(True)
        settings_layout.addWidget(self.run_as_admin_cb)
        
        # Exclude app - Hỗ trợ nhiều app cách nhau bằng khoảng trắng
        exclude_label = QLabel("Vô hiệu hóa trong ứng dụng:")
        exclude_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        settings_layout.addWidget(exclude_label)
        
        self.exclude_app_input = QLineEdit()
        self.exclude_app_input.setText("dnplayer.exe")
        self.exclude_app_input.setPlaceholderText("Ví dụ: oncehuman.exe dnd.exe zalo.exe")
        settings_layout.addWidget(self.exclude_app_input)
        
        # Hướng dẫn
        hint_label = QLabel("💡 <i>Nhập nhiều app cách nhau bằng khoảng trắng</i>")
        hint_label.setStyleSheet("color: #999; font-size: 11px; margin-bottom: 10px;")
        settings_layout.addWidget(hint_label)
        
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # About
        about_group = QGroupBox("Thông tin")
        about_layout = QVBoxLayout()
        about_text = QLabel(
            "<b>AHK Manager v1.0.0</b><br>"
            "Công cụ quản lý AutoHotkey Script<br><br>"
            "<b>Hướng dẫn:</b><br>"
            "• <b>Hotstring</b>: Nhập text thường (vd: dd, xx, ww)<br>"
            "• <b>Hotkey</b>: Dùng ký hiệu đặc biệt:<br>"
            "  - ^ = Ctrl (vd: ^1 = Ctrl+1)<br>"
            "  - ! = Alt (vd: !a = Alt+A)<br>"
            "  - + = Shift (vd: +^a = Shift+Ctrl+A)<br>"
            "  - # = Win (vd: #e = Win+E)<br>"
        )
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)
        
        layout.addStretch()
        
        return tab
    
    def delete_hotkey(self):
        """Xóa hotkey đã chọn - Xóa cả hàng dựa trên ô được chọn"""
        # Lấy ô hiện tại được chọn (có thể là bất kỳ ô nào trong hàng)
        current_item = self.hotkey_table.currentItem()
        
        if not current_item:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng click vào 1 ô bất kỳ trong hàng cần xóa!")
            return
        
        # Lấy số hàng từ ô được chọn
        row_to_delete = current_item.row()
        
        # Lấy thông tin hotkey để hiển thị
        trigger_item = self.hotkey_table.item(row_to_delete, 0)
        trigger_text = trigger_item.text() if trigger_item else "N/A"
        
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa hotkey [{trigger_text}]?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            hotkeys = self.manager.load_hotkeys()
            
            if row_to_delete < len(hotkeys):
                del hotkeys[row_to_delete]
                
                if self.manager.save_hotkeys(hotkeys):
                    self.load_data()
                    self.statusBar().showMessage(f"✅ Đã xóa hotkey [{trigger_text}]", 3000)
    
    def add_empty_row(self):
        """Thêm hàng trống mới vào bảng"""
        # Block signal to prevent on_table_item_changed
        self.hotkey_table.blockSignals(True)
        
        row_count = self.hotkey_table.rowCount()
        self.hotkey_table.insertRow(row_count)
        
        # Trigger (empty)
        self.hotkey_table.setItem(row_count, 0, QTableWidgetItem(""))
        
        # Type (combobox - NO SCROLL)
        type_combo = NoScrollComboBox()
        type_combo.addItems([
            "SendInput", "Send", "SendEvent", "SendRaw", "Clipboard", "Delay", "ExcludeApp"
        ])
        type_combo.currentTextChanged.connect(lambda text, r=row_count: self.on_type_changed(r, text))
        self.hotkey_table.setCellWidget(row_count, 1, type_combo)
        
        # Output (empty)
        self.hotkey_table.setItem(row_count, 2, QTableWidgetItem(""))
        
        # Delay (default 100)
        self.hotkey_table.setItem(row_count, 3, QTableWidgetItem("100"))
        
        # Status (enabled)
        status_item = QTableWidgetItem("✅ Bật")
        self.hotkey_table.setItem(row_count, 4, status_item)
        
        # Description (empty)
        self.hotkey_table.setItem(row_count, 5, QTableWidgetItem(""))
        
        self.hotkey_table.blockSignals(False)
        self.statusBar().showMessage(f"✅ Đã thêm hàng mới #{row_count + 1}", 3000)
    
    def on_type_changed(self, row: int, output_type: str):
        """Xử lý khi thay đổi loại output"""
        # Nếu là ExcludeApp, không cần trigger
        if output_type == "ExcludeApp":
            item = self.hotkey_table.item(row, 0)
            if item:
                item.setText("")
                item.setBackground(QColor("#3a3a3a"))  # Disabled color
    
    def on_table_item_changed(self, item):
        """Xử lý khi cell được edit"""
        # Auto-save hoặc mark as modified
        pass
    
    def validate_duplicate_triggers(self, hotkeys: List) -> tuple:
        """Kiểm tra trùng lặp hotkey trigger
        Returns: (is_valid, duplicate_triggers_list)
        """
        triggers = {}
        duplicates = []
        
        for idx, hotkey in enumerate(hotkeys):
            trigger = hotkey.trigger.lower().strip()
            if not trigger:
                continue
                
            if trigger in triggers:
                duplicates.append(f"• '{hotkey.trigger}' (hàng {triggers[trigger]+1} và {idx+1})")
                triggers[trigger] = idx
            else:
                triggers[trigger] = idx
        
        return (len(duplicates) == 0, duplicates)
    
    def validate_duplicate_exclude_apps(self) -> tuple:
        """Kiểm tra trùng lặp exclude app giữa table và settings
        Returns: (is_valid, duplicate_apps_list)
        """
        # Lấy exclude apps từ table
        table_apps = set()
        for row in range(self.hotkey_table.rowCount()):
            type_widget = self.hotkey_table.cellWidget(row, 1)
            if type_widget and type_widget.currentText() == "ExcludeApp":
                output_item = self.hotkey_table.item(row, 2)
                if output_item:
                    app = output_item.text().strip().lower()
                    if app:
                        table_apps.add(app)
        
        # Lấy exclude apps từ settings
        settings_apps = set()
        if hasattr(self, 'exclude_app_input'):
            settings_text = self.exclude_app_input.text().strip()
            if settings_text:
                # Split bằng khoảng trắng
                for app in settings_text.split():
                    app = app.strip().lower()
                    if app:
                        settings_apps.add(app)
        
        # Tìm app trùng lặp
        duplicates = table_apps.intersection(settings_apps)
        
        if duplicates:
            dup_list = [f"• {app}" for app in sorted(duplicates)]
            return (False, dup_list)
        
        return (True, [])
    
    def save_changes(self):
        """Lưu thay đổi vào database và overwrite file AHK hiện tại"""
        print("🔍 DEBUG: save_changes() started")
        try:
            print("🔍 DEBUG: Calling collect_hotkeys_from_table()")
            hotkeys = self.collect_hotkeys_from_table()
            print(f"🔍 DEBUG: Collected {len(hotkeys)} hotkeys")
            
            if not hotkeys:
                print("🔍 DEBUG: No hotkeys found, showing warning")
                QMessageBox.warning(self, "Cảnh báo", "Không có hotkey nào để lưu!")
                return
            
            # ✅ Validation 1: Kiểm tra trùng lặp hotkey trigger
            print("🔍 DEBUG: Validating duplicate triggers...")
            is_valid, duplicate_triggers = self.validate_duplicate_triggers(hotkeys)
            if not is_valid:
                warning_msg = "⚠️ Phát hiện hotkey trùng lặp:\n\n" + "\n".join(duplicate_triggers)
                warning_msg += "\n\n❓ Bạn có muốn tiếp tục lưu không?"
                reply = QMessageBox.warning(
                    self, "Cảnh báo: Hotkey trùng lặp",
                    warning_msg,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    print("🔍 DEBUG: User cancelled save due to duplicate triggers")
                    return
            
            # ✅ Validation 2: Kiểm tra trùng lặp exclude app
            print("🔍 DEBUG: Validating duplicate exclude apps...")
            is_valid, duplicate_apps = self.validate_duplicate_exclude_apps()
            if not is_valid:
                warning_msg = "⚠️ Phát hiện ứng dụng exclude trùng lặp giữa bảng và cài đặt:\n\n"
                warning_msg += "\n".join(duplicate_apps)
                warning_msg += "\n\n💡 Gợi ý: Chỉ nên định nghĩa exclude app ở 1 nơi (bảng HOẶC cài đặt)"
                warning_msg += "\n\n❓ Bạn có muốn tiếp tục lưu không?"
                reply = QMessageBox.warning(
                    self, "Cảnh báo: Exclude App trùng lặp",
                    warning_msg,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    print("🔍 DEBUG: User cancelled save due to duplicate exclude apps")
                    return
            
            # Save to database
            print("🔍 DEBUG: Saving hotkeys to database...")
            if self.manager.save_hotkeys(hotkeys):
                print("🔍 DEBUG: Hotkeys saved to database successfully")
                
                # Generate and overwrite current AHK file
                # Priority: opened file > default
                output_path = self.opened_ahk_file if self.opened_ahk_file else self.current_ahk_file
                print(f"🔍 DEBUG: Output path (opened/default): {output_path}")
                
                print("🔍 DEBUG: Getting exclude apps from table...")
                exclude_apps = self.get_exclude_apps_from_table()
                print(f"🔍 DEBUG: Exclude apps: {exclude_apps}")
                
                run_as_admin = True
                if hasattr(self, 'run_as_admin_cb'):
                    run_as_admin = self.run_as_admin_cb.isChecked()
                print(f"🔍 DEBUG: Run as admin: {run_as_admin}")
                
                print("🔍 DEBUG: Generating AHK script...")
                if self.manager.generate_ahk_script(hotkeys, output_path, exclude_apps, run_as_admin):
                    print("🔍 DEBUG: Script generated successfully")
                    self.statusBar().showMessage(f"✅ Đã lưu và cập nhật {output_path}", 5000)
                    print("🔍 DEBUG: Showing success message box...")
                    QMessageBox.information(self, "Thành công", f"Đã lưu thay đổi!\n\nFile: {output_path}")
                    print("🔍 DEBUG: Message box shown, function ending normally")
                else:
                    print("🔍 DEBUG: Script generation failed")
                    QMessageBox.critical(self, "Lỗi", "Không thể tạo file AHK!")
            else:
                print("🔍 DEBUG: Failed to save hotkeys to database")
                QMessageBox.critical(self, "Lỗi", "Không thể lưu hotkeys!")
                
            print("🔍 DEBUG: save_changes() completed successfully")
        except Exception as e:
            print(f"🔍 ERROR in save_changes: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi lưu: {e}")
    
    def save_as_ahk(self):
        """Lưu ra file AHK mới"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save as AHK",
                str(Path.home() / "Desktop" / "MyHotkeys.ahk"),
                "AutoHotkey Script (*.ahk);;All Files (*.*)"
            )
            
            if not file_path:
                return
            
            hotkeys = self.collect_hotkeys_from_table()
            
            if not hotkeys:
                QMessageBox.warning(self, "Cảnh báo", "Không có hotkey nào để lưu!")
                return
            
            # ✅ Validation 1: Kiểm tra trùng lặp hotkey trigger
            is_valid, duplicate_triggers = self.validate_duplicate_triggers(hotkeys)
            if not is_valid:
                warning_msg = "⚠️ Phát hiện hotkey trùng lặp:\n\n" + "\n".join(duplicate_triggers)
                warning_msg += "\n\n❓ Bạn có muốn tiếp tục lưu không?"
                reply = QMessageBox.warning(
                    self, "Cảnh báo: Hotkey trùng lặp",
                    warning_msg,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # ✅ Validation 2: Kiểm tra trùng lặp exclude app
            is_valid, duplicate_apps = self.validate_duplicate_exclude_apps()
            if not is_valid:
                warning_msg = "⚠️ Phát hiện ứng dụng exclude trùng lặp giữa bảng và cài đặt:\n\n"
                warning_msg += "\n".join(duplicate_apps)
                warning_msg += "\n\n💡 Gợi ý: Chỉ nên định nghĩa exclude app ở 1 nơi (bảng HOẶC cài đặt)"
                warning_msg += "\n\n❓ Bạn có muốn tiếp tục lưu không?"
                reply = QMessageBox.warning(
                    self, "Cảnh báo: Exclude App trùng lặp",
                    warning_msg,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # Save to database first
            self.manager.save_hotkeys(hotkeys)
            
            # Generate AHK file
            exclude_apps = self.get_exclude_apps_from_table()
            
            run_as_admin = True
            if hasattr(self, 'run_as_admin_cb'):
                run_as_admin = self.run_as_admin_cb.isChecked()
            
            if self.manager.generate_ahk_script(hotkeys, file_path, exclude_apps, run_as_admin):
                # Cập nhật opened file và lưu session
                self.opened_ahk_file = file_path
                self.current_file_label.setText(f"📄 File: <b>{file_path}</b>")
                self.current_file_label.setStyleSheet("color: #2a82da; font-size: 11px; padding: 5px;")
                self.manager.save_session(file_path)
                
                self.statusBar().showMessage(f"✅ Đã lưu: {file_path}", 5000)
                QMessageBox.information(self, "Thành công", f"Đã lưu file AHK!\n\n{file_path}")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể tạo file AHK!")
        except Exception as e:
            print(f"🔍 Error in save_as_ahk: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi lưu: {e}")
    
    def display_to_ahk(self, display_str: str) -> str:
        """Convert display format (Ctrl+1) to AHK format (^1)"""
        result = display_str
        result = result.replace('Ctrl+', '^')
        result = result.replace('Alt+', '!')
        result = result.replace('Shift+', '+')
        result = result.replace('Win+', '#')
        return result
    
    def get_exclude_apps_from_table(self) -> str:
        """Lấy danh sách ExcludeApp từ bảng"""
        exclude_apps = []
        
        for row in range(self.hotkey_table.rowCount()):
            type_widget = self.hotkey_table.cellWidget(row, 1)
            if type_widget and type_widget.currentText() == "ExcludeApp":
                output_item = self.hotkey_table.item(row, 2)
                if output_item:
                    apps = output_item.text().strip()
                    if apps:
                        exclude_apps.append(apps)
        
        return " ".join(exclude_apps)
    
    def collect_hotkeys_from_table(self) -> List[HotkeyItem]:
        """Thu thập tất cả hotkeys từ bảng"""
        print("🔍 DEBUG: collect_hotkeys_from_table() started")
        hotkeys = []
        
        row_count = self.hotkey_table.rowCount()
        print(f"🔍 DEBUG: Table has {row_count} rows")
        
        for row in range(row_count):
            print(f"🔍 DEBUG: Processing row {row}")
            try:
                # Get trigger
                trigger_item = self.hotkey_table.item(row, 0)
                trigger = trigger_item.text().strip() if trigger_item else ""
                
                # Convert display format back to AHK if needed (Ctrl+1 → ^1)
                if '+' in trigger and any(mod in trigger for mod in ['Ctrl', 'Alt', 'Shift', 'Win']):
                    trigger = self.display_to_ahk(trigger)
                
                print(f"🔍 DEBUG: Row {row} - Trigger: '{trigger}'")
                
                # Get type
                type_widget = self.hotkey_table.cellWidget(row, 1)
                output_type = type_widget.currentText() if type_widget else "SendInput"
                print(f"🔍 DEBUG: Row {row} - Type: '{output_type}'")
                
                # Get output
                output_item = self.hotkey_table.item(row, 2)
                output_value = output_item.text().strip() if output_item else ""
                print(f"🔍 DEBUG: Row {row} - Output: '{output_value[:30]}...'")
                
                # Get delay
                delay_item = self.hotkey_table.item(row, 3)
                try:
                    delay = int(delay_item.text()) if delay_item else 100
                except:
                    delay = 100
                print(f"🔍 DEBUG: Row {row} - Delay: {delay}")
                
                # Get status
                status_item = self.hotkey_table.item(row, 4)
                enabled = "✅" in status_item.text() if status_item else True
                print(f"🔍 DEBUG: Row {row} - Enabled: {enabled}")
                
                # Get description
                desc_item = self.hotkey_table.item(row, 5)
                description = desc_item.text().strip() if desc_item else ""
                
                # Skip empty rows
                # ExcludeApp không cần trigger, chỉ cần output (app name)
                if output_type == "ExcludeApp":
                    if not output_value:
                        print(f"🔍 DEBUG: Row {row} - Skipping empty ExcludeApp")
                        continue
                    # ExcludeApp có thể không có trigger
                    trigger = trigger or ""
                else:
                    # Các loại khác phải có cả trigger và output
                    if not trigger or not output_value:
                        print(f"🔍 DEBUG: Row {row} - Skipping empty row")
                        continue
                
                hotkey = HotkeyItem(
                    trigger=trigger,
                    output_type=output_type,
                    output_value=output_value,
                    delay=delay,
                    enabled=enabled,
                    description=description
                )
                hotkeys.append(hotkey)
                print(f"🔍 DEBUG: Row {row} - Hotkey added successfully")
                
            except Exception as e:
                print(f"🔍 ERROR processing row {row}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"🔍 DEBUG: collect_hotkeys_from_table() returning {len(hotkeys)} hotkeys")
        return hotkeys
    
    def load_data(self):
        """Load và hiển thị dữ liệu"""
        self.hotkey_table.blockSignals(True)
        
        hotkeys = self.manager.load_hotkeys()
        
        self.hotkey_table.setRowCount(len(hotkeys))
        
        for row, hotkey in enumerate(hotkeys):
            # Trigger
            self.hotkey_table.setItem(row, 0, QTableWidgetItem(hotkey.trigger))
            
            # Type (combobox - NO SCROLL)
            type_combo = NoScrollComboBox()
            type_combo.addItems([
                "SendInput", "Send", "SendEvent", "SendRaw", "Clipboard", "Delay", "ExcludeApp"
            ])
            type_combo.setCurrentText(hotkey.output_type)
            type_combo.currentTextChanged.connect(lambda text, r=row: self.on_type_changed(r, text))
            self.hotkey_table.setCellWidget(row, 1, type_combo)
            
            # Output - Hiển thị đầy đủ, không rút gọn
            self.hotkey_table.setItem(row, 2, QTableWidgetItem(hotkey.output_value))
            
            # Delay
            self.hotkey_table.setItem(row, 3, QTableWidgetItem(str(hotkey.delay)))
            
            # Status
            status_item = QTableWidgetItem("✅ Bật" if hotkey.enabled else "❌ Tắt")
            if not hotkey.enabled:
                status_item.setForeground(QColor("#999"))
            self.hotkey_table.setItem(row, 4, status_item)
            
            # Description
            self.hotkey_table.setItem(row, 5, QTableWidgetItem(hotkey.description))
        
        self.hotkey_table.blockSignals(False)
        self.statusBar().showMessage(f"Đã load {len(hotkeys)} hotkey", 2000)
    
    def open_ahk_file(self):
        """Mở file AHK và load vào table"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file AHK để mở",
            str(Path.home() / "Desktop"),
            "AutoHotkey Script (*.ahk);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        print(f"🔍 DEBUG: Opening AHK file: {file_path}")
        
        # Parse AHK file (simple parser)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            hotkeys = []
            current_trigger = None
            current_description = ""
            current_commands = []
            
            for line in lines:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith(';'):
                    if line.startswith(';') and not line.startswith('; ='):
                        current_description = line[1:].strip()
                    continue
                
                # Detect trigger
                if line.startswith('::') and line.endswith('::'):
                    # Hotstring
                    trigger = line[2:-2]
                    current_trigger = trigger
                    current_commands = []
                elif '::' in line and not line.startswith('#If'):
                    # Hotkey
                    trigger = line.split('::')[0]
                    current_trigger = trigger
                    current_commands = []
                elif line.lower() == 'return':
                    # End of hotkey block
                    if current_trigger and current_commands:
                        # Parse commands
                        output_type = "SendInput"
                        output_value = ""
                        delay = 100
                        
                        for cmd in current_commands:
                            if cmd.lower().startswith('sendinput '):
                                output_type = "SendInput"
                                output_value = cmd[10:]
                            elif cmd.lower().startswith('send, '):
                                output_type = "Send"
                                output_value = cmd[6:]
                            elif cmd.lower().startswith('sendevent '):
                                output_type = "SendEvent"
                                output_value = cmd[10:]
                            elif cmd.lower().startswith('sleep '):
                                delay = int(cmd[6:])
                        
                        if output_value:
                            hotkey = HotkeyItem(
                                trigger=current_trigger,
                                output_type=output_type,
                                output_value=output_value,
                                delay=delay,
                                enabled=True,
                                description=current_description
                            )
                            hotkeys.append(hotkey)
                        
                        current_trigger = None
                        current_description = ""
                        current_commands = []
                else:
                    if current_trigger:
                        current_commands.append(line)
            
            if hotkeys:
                print(f"🔍 DEBUG: Parsed {len(hotkeys)} hotkeys from file")
                
                # KHÔNG merge - thay thế hoàn toàn
                print("🔍 DEBUG: Saving hotkeys to database...")
                if self.manager.save_hotkeys(hotkeys):
                    print("🔍 DEBUG: Hotkeys saved successfully")
                    
                    # Update opened file tracking
                    self.opened_ahk_file = file_path
                    print(f"🔍 DEBUG: Set opened_ahk_file to: {file_path}")
                    
                    # Update label
                    try:
                        self.current_file_label.setText(f"📄 File: <b>{file_path}</b>")
                        self.current_file_label.setStyleSheet("color: #2a82da; font-size: 11px; padding: 5px;")
                        print("🔍 DEBUG: Updated file label")
                    except Exception as label_error:
                        print(f"🔍 ERROR updating label: {label_error}")
                    
                    # Reload table
                    print("🔍 DEBUG: Reloading table data...")
                    try:
                        self.load_data()
                        print("🔍 DEBUG: Table reloaded successfully")
                    except Exception as load_error:
                        print(f"🔍 ERROR loading data: {load_error}")
                        import traceback
                        traceback.print_exc()
                    
                    # Lưu session
                    self.manager.save_session(file_path)
                    print(f"🔍 DEBUG: Saved session with file: {file_path}")
                    
                    self.statusBar().showMessage(f"✅ Đã mở file: {Path(file_path).name}", 5000)
                    print("🔍 DEBUG: Showing success message...")
                    QMessageBox.information(
                        self, "Thành công",
                        f"Đã mở file AHK!\n\nFile: {file_path}\nHotkeys: {len(hotkeys)}"
                    )
                    print("🔍 DEBUG: open_ahk_file completed successfully")
                else:
                    print("🔍 ERROR: Failed to save hotkeys")
                    QMessageBox.critical(self, "Lỗi", "Không thể lưu hotkeys vào database!")
            else:
                print("🔍 DEBUG: No hotkeys found in file")
                QMessageBox.warning(self, "Cảnh báo", "Không tìm thấy hotkey nào trong file!")
                
        except Exception as e:
            print(f"🔍 ERROR opening AHK file: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể mở file AHK: {e}")
    
    def restore_session(self):
        """Khôi phục session (file đã mở lần trước) hoặc clear data nếu file không tồn tại"""
        session = self.manager.load_session()
        opened_file = session.get("opened_file")
        
        if opened_file and Path(opened_file).exists():
            # File còn tồn tại → Load data từ database
            self.opened_ahk_file = opened_file
            self.current_file_label.setText(f"📄 File: <b>{opened_file}</b>")
            self.current_file_label.setStyleSheet("color: #2a82da; font-size: 11px; padding: 5px;")
            print(f"🔍 DEBUG: Restored session - opened file: {opened_file}")
            self.load_data()
        else:
            # File không tồn tại hoặc không có session → Clear database + hiển thị bảng trống
            print("🔍 DEBUG: No valid session file - clearing database and showing empty table")
            self.current_file_label.setText("📄 File: <i>Chưa mở file nào</i>")
            self.current_file_label.setStyleSheet("color: #999; font-size: 11px; padding: 5px;")
            
            # Clear database
            self.manager.save_hotkeys([])
            self.manager.save_session(None)
            
            # Hiển thị bảng trống
            self.hotkey_table.setRowCount(0)
            print("🔍 DEBUG: Table cleared - waiting for user to open a file")
    
    def closeEvent(self, event):
        """Xử lý khi đóng ứng dụng"""
        # Lưu session trước khi thoát
        self.manager.save_session(self.opened_ahk_file)
        
        if self.ahk_process and self.ahk_process.state() == QProcess.Running:
            reply = QMessageBox.question(
                self, "Xác nhận thoát",
                "Script AHK đang chạy. Bạn có muốn dừng nó trước khi thoát?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                self.stop_script()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = AHKManagerGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

