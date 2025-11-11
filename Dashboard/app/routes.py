from flask import render_template
from flask import current_app as app

@app.route('/')
def home():
    """Render trang chủ."""
    return render_template('home.html', title='Trang Chủ')

@app.route('/telegram')
def telegram():
    """Render trang quản lý Telegram."""
    return render_template('telegram.html', title='Quản Lý Telegram')

@app.route('/notes')
def notes():
    """Render trang ghi chú."""
    return render_template('notes.html', title='Ghi Chú')

