# Mon Project Structure

Dự án được tổ chức thành 3 thư mục chính:

## 📁 Cấu trúc thư mục

### 1. **Dashboard/**
Dashboard web Flask để quản lý các công cụ và dữ liệu.

**Chạy dashboard:**
```bash
cd Dashboard
python run.pyw
```

**Nội dung:**
- `app/` - Flask application code
- `data/` - Database và file dữ liệu
- `static/` - CSS/JS files
- `templates/` - HTML templates
- `run.pyw` - File khởi động chính

---

### 2. **Android_Tool/**
Công cụ quản lý và tương tác với thiết bị Android.

**Chạy Android Tool:**
```bash
cd Android_Tool
python Main.pyw
```

**Nội dung:**
- `modules/` - Các module chức năng (ModAndroid, Notes, Telegram)
- `icons/` - Icons cho giao diện
- `logs/` - Log files
- `Main.pyw` - File khởi động chính

---

### 3. **AHK_Tool/**
Công cụ AutoHotkey để tự động hóa các tác vụ Windows.

**Chạy AHK Tool:**
```bash
cd AHK_Tool
python AHK_Manager.py
```

**Nội dung:**
- `AHK_Manager.py` - Quản lý AHK scripts
- `AHK_Mon.ahk` - AutoHotkey scripts

---

## 🚀 Quick Start

1. Cài đặt dependencies (nếu cần):
```bash
cd Dashboard
pip install -r requirements.txt
```

2. Chạy Dashboard:
```bash
cd Dashboard
python run.pyw
```

3. Truy cập: http://127.0.0.1:5000

---

## 📝 Notes

- Mỗi thư mục là một ứng dụng độc lập
- Dashboard có thể quản lý và tích hợp với các tool khác
- Tất cả các file quan trọng đã được tổ chức gọn gàng theo chức năng

