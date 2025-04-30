from flask import Flask, render_template, redirect, url_for, request, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import timedelta, datetime
import cloudinary
import cloudinary.uploader
import io
import requests

from config import Config
from models import db, User, File

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET
)

@app.before_request
def session_timeout():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=1)
    session.modified = True

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists!')
            return redirect(url_for('register'))
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    if file:
        upload_result = cloudinary.uploader.upload(file)
        new_file = File(
            filename=file.filename,
            url=upload_result['secure_url'],
            public_id=upload_result['public_id'],
            user_id=current_user.id
        )
        db.session.add(new_file)
        db.session.commit()
        flash('File uploaded successfully!')
    return redirect(url_for('dashboard'))

@app.route('/files')
@login_required
def files():
    user_files = File.query.filter_by(user_id=current_user.id).all()
    return render_template('view_files.html', files=user_files)

@app.route('/download/<int:file_id>')
@login_required
def download(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash("You do not have permission to download this file.")
        return redirect(url_for('files'))
    
    response = requests.get(file.url)
    return send_file(io.BytesIO(response.content), download_name=file.filename, as_attachment=True)

@app.route('/delete/<int:file_id>', methods=['POST'])
@login_required
def delete(file_id):
    file = File.query.get_or_404(file_id)
    if file.user_id != current_user.id:
        flash("You do not have permission to delete this file.")
        return redirect(url_for('files'))

    cloudinary.uploader.destroy(file.public_id)
    db.session.delete(file)
    db.session.commit()
    flash('File deleted successfully!')
    return redirect(url_for('files'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# (Everything else above remains unchanged...)

@app.route('/initdb')
def initdb():
    try:
        db.create_all()
        return "Database initialized successfully!"
    except Exception as e:
        return f"Database initialization failed: {e}", 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
