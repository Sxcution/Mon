"""
Notes Module - Quản lý ghi chú với database SQLite
Port từ index.html và Mainold.pyw
"""

import os
import sys
import sqlite3
import uuid
from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QRect, QPoint
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QMessageBox, QCheckBox, QDateTimeEdit, QComboBox,
    QSplitter, QFrame, QMenu, QColorDialog, QInputDialog, QStyle, QStyledItemDelegate
)
from PyQt6.QtGui import QFont, QColor, QFocusEvent, QAction, QTextCursor, QTextCharFormat, QDesktopServices, QPainter, QPen
from PyQt6.QtCore import QDateTime
import re

# Configuration
tool_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(tool_dir, "data")
os.makedirs(data_dir, exist_ok=True)

DATABASE_PATH = os.path.join(data_dir, "notes.db")


class NoteTitleDelegate(QStyledItemDelegate):
    """Custom delegate to render title on left and time on right in the same cell."""
    
    def paint(self, painter, option, index):
        """Override paint to draw title and time separately."""
        # Get the full text (title|||time format)
        full_text = index.data(Qt.ItemDataRole.DisplayRole)
        if not full_text:
            return
        
        # Split title and time
        parts = full_text.split("|||")
        title = parts[0] if len(parts) > 0 else ""
        time_str = parts[1] if len(parts) > 1 else ""
        
        # Get font and color from index data
        font_data = index.data(Qt.ItemDataRole.FontRole)
        color_data = index.data(Qt.ItemDataRole.ForegroundRole)
        
        if font_data:
            font = font_data
        else:
            font = QFont()
            font.setBold(True)
        
        if color_data:
            color = color_data
        else:
            color = QColor("#ffffff")
        
        painter.save()
        
        # Draw xeon border if selected (NO background fill)
        if option.state & QStyle.StateFlag.State_Selected:
            # Draw glowing xeon blue border
            pen = QPen(QColor("#00aaff"))
            pen.setWidth(2)
            painter.setPen(pen)
            # Draw border with small inset
            border_rect = option.rect.adjusted(1, 1, -1, -1)
            painter.drawRect(border_rect)
            
            # Optional: Draw inner glow effect
            pen.setWidth(1)
            pen.setColor(QColor("#00aaff"))
            painter.setPen(pen)
            inner_rect = option.rect.adjusted(2, 2, -2, -2)
            painter.drawRect(inner_rect)
        
        # Draw title on left (bold)
        painter.setFont(font)
        painter.setPen(color)
        title_rect = QRect(option.rect.left() + 8, option.rect.top(), 
                          option.rect.width() - 150, option.rect.height())
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        
        # Draw time on right (gray, not bold)
        if time_str:
            time_font = QFont(font)
            time_font.setBold(False)
            painter.setFont(time_font)
            painter.setPen(QColor("#888888"))
            time_rect = QRect(option.rect.right() - 140, option.rect.top(),
                            130, option.rect.height())
            painter.drawText(time_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, time_str)
        
        painter.restore()


class AutoSaveLineEdit(QLineEdit):
    """QLineEdit with auto-save on focus out."""
    focusOut = pyqtSignal()
    
    def focusOutEvent(self, event: QFocusEvent):
        """Emit signal when focus is lost."""
        super().focusOutEvent(event)
        self.focusOut.emit()


class AutoSaveTextEdit(QTextEdit):
    """QTextEdit with auto-save on focus out and custom context menu."""
    focusOut = pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_custom_context_menu)
        self.setAcceptRichText(True)  # Enable rich text
        
    def focusOutEvent(self, event: QFocusEvent):
        """Emit signal when focus is lost."""
        super().focusOutEvent(event)
        self.focusOut.emit()
    
    def show_custom_context_menu(self, position):
        """Show custom context menu."""
        menu = QMenu(self)
        
        cursor = self.textCursor()
        has_selection = cursor.hasSelection()
        
        # Change text color (only if has selection)
        if has_selection:
            color_action = QAction("🎨 Đổi màu chữ", self)
            color_action.triggered.connect(self.change_text_color)
            menu.addAction(color_action)
            menu.addSeparator()
        
        # Text size submenu (always show)
        size_menu = QMenu("📏 Text size", self)
        
        # Quick size options
        for size in [8, 10, 12, 14, 16, 18, 20, 24, 28, 32]:
            size_action = QAction(f"{size}pt", self)
            size_action.triggered.connect(lambda checked, s=size: self.change_text_size(s))
            size_menu.addAction(size_action)
        
        size_menu.addSeparator()
        
        # Custom size
        custom_size_action = QAction("✏️ Tùy chỉnh...", self)
        custom_size_action.triggered.connect(self.change_text_size_custom)
        size_menu.addAction(custom_size_action)
        
        menu.addMenu(size_menu)
        menu.addSeparator()
        
        # Add link
        link_action = QAction("🔗 Gán link", self)
        link_action.triggered.connect(self.insert_link)
        menu.addAction(link_action)
        
        # Check if cursor is on a link (check anchor format from HTML)
        cursor_at_pos = self.cursorForPosition(position)
        char_format = cursor_at_pos.charFormat()
        if char_format.isAnchor():
            link_url = char_format.anchorHref()
            if link_url:
                menu.addSeparator()
                open_link_action = QAction("🌐 Mở link", self)
                open_link_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(link_url)))
                menu.addAction(open_link_action)
        
        menu.exec(self.viewport().mapToGlobal(position))
    
    def change_text_color(self):
        """Change color of selected text."""
        color = QColorDialog.getColor()
        if color.isValid():
            cursor = self.textCursor()
            if cursor.hasSelection():
                fmt = QTextCharFormat()
                fmt.setForeground(color)
                cursor.mergeCharFormat(fmt)
    
    def change_text_size(self, size):
        """Change font size of selected text or set for new text."""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        
        if cursor.hasSelection():
            # Apply to selected text
            cursor.mergeCharFormat(fmt)
        else:
            # Set for new text to be typed
            self.setCurrentCharFormat(fmt)
    
    def change_text_size_custom(self):
        """Change font size with custom input."""
        size, ok = QInputDialog.getInt(self, "Text size", "Nhập kích cỡ chữ (pt):", 12, 1, 200)
        if ok:
            self.change_text_size(size)
    
    def insert_link(self):
        """Insert hyperlink."""
        cursor = self.textCursor()
        
        # Get link URL
        url, ok = QInputDialog.getText(self, "Gán link", "Nhập URL:")
        if ok and url:
            if cursor.hasSelection():
                # Link the selected text
                text = cursor.selectedText()
                html = f'<a href="{url}" style="color: #3b82f6; text-decoration: underline;">{text}</a>'
                cursor.insertHtml(html)
            else:
                # Insert URL as text and link
                html = f'<a href="{url}" style="color: #3b82f6; text-decoration: underline;">{url}</a>'
                cursor.insertHtml(html)


class NotesDatabase:
    """Manager for notes SQLite database."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database schema."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                due_time TEXT,
                status TEXT DEFAULT 'none',
                is_marked INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_note(self, title, content=""):
        """Add new note."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        note_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO notes (id, title, content, due_time, status, created_at, modified_at)
            VALUES (?, ?, ?, NULL, 'none', ?, ?)
        """, (note_id, title, content, now, now))
        
        conn.commit()
        conn.close()
        return note_id
    
    def update_note(self, note_id, title, content=""):
        """Update existing note."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            UPDATE notes 
            SET title = ?, content = ?, modified_at = ?
            WHERE id = ?
        """, (title, content, now, note_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def delete_note(self, note_id):
        """Delete note by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def toggle_mark(self, note_id):
        """Toggle mark status."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET is_marked = NOT is_marked WHERE id = ?", (note_id,))
        conn.commit()
        conn.close()
    
    def get_all_notes(self, search_query="", filter_marked=False):
        """Get all notes with optional search and filter."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM notes WHERE 1=1"
        params = []
        
        if search_query:
            query += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        
        if filter_marked:
            query += " AND is_marked = 1"
        
        query += " ORDER BY modified_at DESC"
        
        cursor.execute(query, params)
        notes = cursor.fetchall()
        conn.close()
        
        return [dict(note) for note in notes]


class NotesWidget(QWidget):
    """Notes manager widget."""
    
    def __init__(self, shared_log=None):
        super().__init__()
        self.db = NotesDatabase(DATABASE_PATH)
        self.current_note_id = None
        self.shared_log = shared_log
        self.original_title = ""
        self.original_content = ""
        self.init_ui()
        self.load_notes()
    
    def log(self, message):
        """Log message to shared log output."""
        if self.shared_log:
            self.shared_log.append(message)
    
    def get_relative_time(self, iso_time_str):
        """Convert ISO timestamp to relative time string."""
        try:
            dt = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            diff = now - dt
            
            seconds = int(diff.total_seconds())
            
            if seconds < 60:
                return f"{seconds} giây trước"
            elif seconds < 3600:
                minutes = seconds // 60
                return f"{minutes} phút trước"
            elif seconds < 86400:
                hours = seconds // 3600
                return f"{hours} giờ trước"
            elif seconds < 604800:
                days = seconds // 86400
                return f"{days} ngày trước"
            elif seconds < 2592000:
                weeks = seconds // 604800
                return f"{weeks} tuần trước"
            else:
                months = seconds // 2592000
                return f"{months} tháng trước"
        except:
            return ""
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # ===== TOP BAR: Search + Reminder + Add Button =====
        top_bar = QHBoxLayout()
        
        # Search box - giới hạn chiều rộng để khớp với danh sách ghi chú
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Tìm kiếm ghi chú (Enter để tìm)...")
        self.search_input.textChanged.connect(lambda: self.load_notes(log_search=False))
        self.search_input.returnPressed.connect(lambda: self.load_notes(log_search=True))
        self.search_input.setMaximumWidth(400)  # Giới hạn chiều rộng
        top_bar.addWidget(self.search_input)
        
        top_bar.addStretch()
        
        # Add note button
        add_btn = QPushButton("➕ Tạo Ghi Chú Mới")
        add_btn.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        add_btn.clicked.connect(self.add_new_note)
        add_btn.setMaximumWidth(160)
        top_bar.addWidget(add_btn)
        
        layout.addLayout(top_bar)
        
        # ===== SPLITTER: Notes List | Editor =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT: Notes list table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.notes_table = QTableWidget()
        self.notes_table.setColumnCount(2)
        self.notes_table.setHorizontalHeaderLabels(["Danh Sách Ghi Chú", "ID"])
        self.notes_table.setColumnHidden(1, True)  # Hide ID column
        self.notes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.notes_table.verticalHeader().setVisible(False)  # Hide row numbers
        self.notes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.notes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.notes_table.cellClicked.connect(self.on_note_selected)
        self.notes_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.notes_table.customContextMenuRequested.connect(self.show_context_menu)
        # Remove focus border
        self.notes_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Set custom delegate for column 0 to render title and time separately
        self.notes_table.setItemDelegateForColumn(0, NoteTitleDelegate())
        # Custom stylesheet: Remove background when selected, keep xeon border (drawn by delegate)
        self.notes_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: transparent;
                color: inherit;
            }
            QTableWidget::item:focus {
                outline: none;
                background-color: transparent;
            }
        """)
        left_layout.addWidget(self.notes_table)
        
        splitter.addWidget(left_widget)
        
        # RIGHT: Editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        self.title_input = AutoSaveLineEdit()
        self.title_input.setPlaceholderText("Nhập tiêu đề ghi chú...")
        self.title_input.focusOut.connect(self.auto_save_on_focus_out)
        # Set bold font for title
        title_font = self.title_input.font()
        title_font.setBold(True)
        self.title_input.setFont(title_font)
        right_layout.addWidget(self.title_input)
        
        # Content
        self.content_input = AutoSaveTextEdit()
        self.content_input.setPlaceholderText("Nhập nội dung ghi chú...")
        self.content_input.focusOut.connect(self.auto_save_on_focus_out)
        right_layout.addWidget(self.content_input)
        
        splitter.addWidget(right_widget)
        
        # Set splitter sizes (40% list, 60% editor)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
    
    def load_notes(self, log_search=False):
        """Load notes from database to table."""
        search_query = self.search_input.text()
        
        notes = self.db.get_all_notes(search_query, False)
        
        self.notes_table.setRowCount(0)
        
        # Only log when Enter is pressed
        if search_query and log_search:
            self.log(f"🔍 Tìm kiếm: '{search_query}' - Tìm thấy {len(notes)} ghi chú")
        
        for note in notes:
            row = self.notes_table.rowCount()
            self.notes_table.insertRow(row)
            
            # Column 0: Title|||Time format (will be rendered by custom delegate)
            relative_time = self.get_relative_time(note['modified_at'])
            display_text = f"{note['title']}|||{relative_time}" if relative_time else f"{note['title']}|||"
            
            title_item = QTableWidgetItem(display_text)
            
            # Always bold for titles
            font = title_item.font()
            font.setBold(True)
            title_item.setFont(font)
            
            # Gold color for marked notes
            if note['is_marked'] == 1:
                title_item.setForeground(QColor("#FFD700"))
            
            self.notes_table.setItem(row, 0, title_item)
            
            # Column 1: ID (hidden)
            self.notes_table.setItem(row, 1, QTableWidgetItem(note['id']))
    
    def toggle_mark(self, note_id):
        """Toggle mark for note."""
        self.db.toggle_mark(note_id)
        self.log("⭐ Đã chuyển trạng thái đánh dấu ghi chú")
        self.load_notes()
    
    def on_note_selected(self, row, column):
        """Handle note selection from table."""
        if row < 0:
            return
        
        note_id = self.notes_table.item(row, 1).text()  # Column 1 is ID
        
        # Load note details
        notes = self.db.get_all_notes()
        selected_note = next((n for n in notes if n['id'] == note_id), None)
        
        if selected_note:
            self.current_note_id = note_id
            self.title_input.setText(selected_note['title'])
            self.content_input.setHtml(selected_note['content'] or "")  # Use setHtml for rich text
            
            # Store original values for change tracking
            self.original_title = selected_note['title']
            self.original_content = selected_note['content'] or ""
            
            self.log(f"📖 Đang chỉnh sửa: {selected_note['title']}")
    
    def add_new_note(self):
        """Clear editor to add new note."""
        self.clear_editor()
        self.title_input.setFocus()
        self.log("➕ Bắt đầu tạo ghi chú mới")
    
    def clear_editor(self):
        """Clear editor fields."""
        self.current_note_id = None
        self.title_input.clear()
        self.content_input.clear()
        self.original_title = ""
        self.original_content = ""
    
    def save_note(self):
        """Save current note."""
        title = self.title_input.text().strip()
        
        if not title:
            QMessageBox.warning(self, "Lỗi", "Tiêu đề không được để trống!")
            self.log("❌ Lỗi: Tiêu đề không được để trống!")
            return
        
        content = self.content_input.toHtml()  # Save as HTML for rich text
        
        if self.current_note_id:
            # Update existing
            success = self.db.update_note(self.current_note_id, title, content)
            if success:
                self.log(f"💾 Đã cập nhật ghi chú: {title}")
                self.load_notes()
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể cập nhật ghi chú!")
                self.log("❌ Lỗi: Không thể cập nhật ghi chú!")
        else:
            # Add new
            note_id = self.db.add_note(title, content)
            self.current_note_id = note_id
            self.log(f"✅ Đã tạo ghi chú mới: {title}")
            self.load_notes()
    
    def delete_note(self):
        """Delete current note."""
        if not self.current_note_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn ghi chú để xóa!")
            self.log("❌ Lỗi: Vui lòng chọn ghi chú để xóa!")
            return
        
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa ghi chú này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.db.delete_note(self.current_note_id)
            if success:
                self.log("🗑️ Đã xóa ghi chú thành công")
                self.clear_editor()
                self.load_notes()
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể xóa ghi chú!")
                self.log("❌ Lỗi: Không thể xóa ghi chú!")
    
    def auto_save_on_focus_out(self):
        """Auto save when focus leaves input fields - only if changed."""
        title = self.title_input.text().strip()
        content = self.content_input.toHtml()
        
        # Check if content has changed
        has_changed = (title != self.original_title or content != self.original_content)
        
        # Only auto-save if there's a title and content has changed
        if title and has_changed:
            self.save_note()
            # Update original values after saving
            self.original_title = title
            self.original_content = content
    
    def show_context_menu(self, position):
        """Show context menu for notes table."""
        # Get selected row
        row = self.notes_table.rowAt(position.y())
        if row < 0:
            return
        
        # Get note ID
        note_id = self.notes_table.item(row, 1).text()  # Column 1 is ID
        
        # Get note details to check mark status
        notes = self.db.get_all_notes()
        selected_note = next((n for n in notes if n['id'] == note_id), None)
        if not selected_note:
            return
        
        # Create context menu
        menu = QMenu(self)
        
        # Mark/Unmark action
        if selected_note['is_marked'] == 1:
            mark_action = QAction("⭐ Bỏ đánh dấu", self)
        else:
            mark_action = QAction("⭐ Đánh dấu", self)
        mark_action.triggered.connect(lambda: self.toggle_mark_from_menu(note_id))
        menu.addAction(mark_action)
        
        menu.addSeparator()
        
        # Delete action
        delete_action = QAction("🗑️ Xóa ghi chú", self)
        delete_action.triggered.connect(lambda: self.delete_note_from_menu(note_id))
        menu.addAction(delete_action)
        
        # Show menu at cursor position
        menu.exec(self.notes_table.viewport().mapToGlobal(position))
    
    def toggle_mark_from_menu(self, note_id):
        """Toggle mark status from context menu."""
        self.db.toggle_mark(note_id)
        self.log("⭐ Đã chuyển trạng thái đánh dấu ghi chú")
        self.load_notes()
    
    def delete_note_from_menu(self, note_id):
        """Delete note from context menu with confirmation."""
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa ghi chú này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.db.delete_note(note_id)
            if success:
                self.log("🗑️ Đã xóa ghi chú thành công")
                # Clear editor if deleted note was selected
                if self.current_note_id == note_id:
                    self.clear_editor()
                self.load_notes()
            else:
                QMessageBox.warning(self, "Lỗi", "Không thể xóa ghi chú!")
                self.log("❌ Lỗi: Không thể xóa ghi chú!")

