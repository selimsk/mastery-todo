import json
import os
import shutil
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy

# To enable Google Drive, run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    DRIVE_SUPPORT = True
except ImportError:
    DRIVE_SUPPORT = False

app = Flask(__name__)
app.secret_key = "study_secret_key" 

# --- Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'study_tracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Backup Paths
BACKUP_DIR = os.path.join(basedir, 'backups')
DB_PATH = os.path.join(basedir, 'study_tracker.db')
ROUTINE_PATH = os.path.join(basedir, 'routine.json')
GOOGLE_CREDENTIALS_FILE = os.path.join(basedir, 'service_account.json')

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

db = SQLAlchemy(app)

# --- Database Models ---

class DailyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    task_data = db.Column(db.Text, nullable=False)

class ProgressHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    score = db.Column(db.Integer, nullable=False)

# --- Routine Logic ---

DEFAULT_ROUTINE = [
    {'id': 'morning-routine', 'time': '05:00 - 05:30', 'title': 'Wake Up & Morning Routine', 'category': 'Health'},
    {'id': 'german-1', 'time': '05:30 - 08:00', 'title': 'German (Deep Study)', 'category': 'German'},
    {'id': 'python-1', 'time': '08:00 - 09:00', 'title': 'Breakfast & Python (Light)', 'category': 'Python'},
    {'id': 'german-flash', 'time': '09:00 - 09:30', 'title': 'German Flashcards (Anki)', 'category': 'German'},
    {'id': 'trade-work', 'time': '09:30 - 13:00', 'title': 'Trade Related Work', 'category': 'Trading'},
    {'id': 'lunch-listening', 'time': '13:00 - 14:00', 'title': 'Lunch & German Listening', 'category': 'German'},
    {'id': 'python-projects', 'time': '14:00 - 15:30', 'title': 'Python Projects', 'category': 'Python'},
    {'id': 'german-conv', 'time': '15:30 - 16:30', 'title': 'German Conversation', 'category': 'German'},
    {'id': 'walking', 'time': '16:30 - 17:30', 'title': 'Walking (German Audio)', 'category': 'Exercise'},
    {'id': 'refresh', 'time': '17:30 - 18:30', 'title': 'Shower & Refresh', 'category': 'Health'},
    {'id': 'german-python-mix', 'time': '18:30 - 20:30', 'title': 'German & Python Mix', 'category': 'Focus'},
    {'id': 'dinner', 'time': '20:30 - 21:30', 'title': 'Dinner & Relaxation', 'category': 'Health'},
    {'id': 'german-ent', 'time': '21:30 - 22:30', 'title': 'German Entertainment', 'category': 'German'},
    {'id': 'journal', 'time': '22:30 - 23:00', 'title': 'Journaling & Planning', 'category': 'Health'},
]

def load_routine():
    if not os.path.exists(ROUTINE_PATH):
        with open(ROUTINE_PATH, 'w') as f:
            json.dump(DEFAULT_ROUTINE, f, indent=4)
        return DEFAULT_ROUTINE
    try:
        with open(ROUTINE_PATH, 'r') as f:
            return json.load(f)
    except:
        return DEFAULT_ROUTINE

# --- Backup and Restore Logic ---

def perform_local_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_dir = os.path.join(BACKUP_DIR, f"temp_{timestamp}")
    os.makedirs(temp_dir)
    
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, os.path.join(temp_dir, 'study_tracker.db'))
    if os.path.exists(ROUTINE_PATH):
        shutil.copy2(ROUTINE_PATH, os.path.join(temp_dir, 'routine.json'))
    
    zip_name = f"backup_{timestamp}"
    shutil.make_archive(os.path.join(BACKUP_DIR, zip_name), 'zip', temp_dir)
    shutil.rmtree(temp_dir)
    return f"{zip_name}.zip"

def upload_to_drive(file_path):
    if not DRIVE_SUPPORT or not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        return False
    try:
        scopes = ['https://www.googleapis.com/auth/drive.file']
        creds = service_account.Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': os.path.basename(file_path)}
        media = MediaFileUpload(file_path, mimetype='application/zip')
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        print(f"Drive backup failed: {e}")
        return False

def auto_backup_thread():
    """Background task to perform auto-backup every 7 days (Weekly)."""
    while True:
        # Wait for 1 week (604,800 seconds)
        time.sleep(604800) 
        try:
            zip_name = perform_local_backup()
            full_path = os.path.join(BACKUP_DIR, zip_name)
            upload_to_drive(full_path)
            print(f"Weekly auto-backup completed: {zip_name}")
        except Exception as e:
            print(f"Weekly auto-backup error: {e}")

# Start the background frequency thread
threading.Thread(target=auto_backup_thread, daemon=True).start()

USER_ID = 'mastery_user_01'

# --- Helpers ---

def get_date_key():
    return datetime.now().strftime('%Y-%m-%d')

def is_current_task(time_range):
    try:
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        start_str, end_str = time_range.split(' - ')
        sh, sm = map(int, start_str.split(':'))
        eh, em = map(int, end_str.split(':'))
        return (sh * 60 + sm) <= current_minutes < (eh * 60 + em)
    except:
        return False

# --- Routes ---

@app.route('/')
def index():
    routine = load_routine()
    date_key = get_date_key()
    record = DailyTask.query.filter_by(user_id=USER_ID, date=date_key).first()
    completed_tasks = json.loads(record.task_data) if record else {}
    done_count = sum(1 for v in completed_tasks.values() if v)
    progress = int((done_count / len(routine)) * 100) if routine else 0
    return render_template('index.html', routine=routine, completed=completed_tasks, progress=progress, date=date_key, check_active=is_current_task, view='today')

@app.route('/history')
def history():
    logs = ProgressHistory.query.filter_by(user_id=USER_ID).order_by(ProgressHistory.date.desc()).limit(10).all()
    return render_template('index.html', logs=logs, view='history', date=get_date_key())

@app.route('/report')
def report():
    logs = ProgressHistory.query.filter_by(user_id=USER_ID).order_by(ProgressHistory.date.desc()).all()
    return render_template('index.html', logs=logs, view='report', date=get_date_key())

@app.route('/settings')
def settings():
    routine = load_routine()
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.zip')], reverse=True)
    return render_template('index.html', routine=routine, backups=backups, view='settings', date=get_date_key(), drive_enabled=DRIVE_SUPPORT)

@app.route('/settings/routine/template')
def download_template():
    """Provides a downloadable JSON template of the current routine."""
    load_routine()  # Ensures routine.json exists
    if os.path.exists(ROUTINE_PATH):
        return send_file(ROUTINE_PATH, as_attachment=True, download_name='routine_template.json')
    flash('Template file could not be found.')
    return redirect(url_for('settings'))

@app.route('/settings/import', methods=['POST'])
def import_routine():
    file = request.files.get('file')
    if file and file.filename.endswith('.json'):
        try:
            data = json.load(file)
            if isinstance(data, list):
                with open(ROUTINE_PATH, 'w') as f:
                    json.dump(data, f, indent=4)
                flash('Routine updated successfully!')
            else:
                flash('Invalid format: Expected a list.')
        except Exception as e:
            flash(f'Error: {e}')
    return redirect(url_for('settings'))

@app.route('/settings/backup/manual')
def manual_backup():
    try:
        zip_name = perform_local_backup()
        full_path = os.path.join(BACKUP_DIR, zip_name)
        drive_status = ""
        if DRIVE_SUPPORT:
            if upload_to_drive(full_path):
                drive_status = " and uploaded to Google Drive"
            else:
                drive_status = " (Drive upload failed)"
        flash(f'Manual backup created: {zip_name}{drive_status}')
    except Exception as e:
        flash(f'Backup failed: {e}')
    return redirect(url_for('settings'))

@app.route('/settings/backup/download/<filename>')
def download_backup(filename):
    path = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    flash('File not found.')
    return redirect(url_for('settings'))

@app.route('/settings/restore', methods=['POST'])
def restore_backup():
    file = request.files.get('file')
    if file and file.filename.endswith('.zip'):
        temp_zip = os.path.join(BACKUP_DIR, 'temp_restore.zip')
        extract_path = os.path.join(BACKUP_DIR, 'temp_extract')
        file.save(temp_zip)
        try:
            shutil.unpack_archive(temp_zip, extract_path)
            db_restore = os.path.join(extract_path, 'study_tracker.db')
            routine_restore = os.path.join(extract_path, 'routine.json')
            if os.path.exists(db_restore):
                db.session.remove() 
                shutil.copy2(db_restore, DB_PATH)
            if os.path.exists(routine_restore):
                shutil.copy2(routine_restore, ROUTINE_PATH)
            flash('System restored! Restarting app logic...')
        except Exception as e:
            flash(f'Restore failed: {e}')
        finally:
            if os.path.exists(temp_zip): os.remove(temp_zip)
            if os.path.exists(extract_path): shutil.rmtree(extract_path)
    return redirect(url_for('settings'))

@app.route('/toggle/<task_id>', methods=['POST'])
def toggle(task_id):
    routine = load_routine()
    date_key = get_date_key()
    record = DailyTask.query.filter_by(user_id=USER_ID, date=date_key).first()
    completed_tasks = json.loads(record.task_data) if record else {}
    completed_tasks[task_id] = not completed_tasks.get(task_id, False)
    if record:
        record.task_data = json.dumps(completed_tasks)
    else:
        db.session.add(DailyTask(user_id=USER_ID, date=date_key, task_data=json.dumps(completed_tasks)))
    score = int((sum(1 for v in completed_tasks.values() if v) / len(routine)) * 100)
    history_record = ProgressHistory.query.filter_by(user_id=USER_ID, date=date_key).first()
    if history_record:
        history_record.score = score
    else:
        db.session.add(ProgressHistory(user_id=USER_ID, date=date_key, score=score))
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
