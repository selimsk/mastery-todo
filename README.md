Mastery IN Todo: Raspberry Pi Study Tracker

A professional, self-hosted Flask application designed for Raspberry Pi to track daily routines, language learning (German), and coding progress (Python).

🚀 Features

Daily Routine Tracking: Smart scheduling from 5:00 AM to 11:00 PM.

Progress Analytics: Performance reports with consistency scoring.

Dynamic Scheduling: Upload a routine.json to change your schedule without restarting the server.

Weekly Backups: Automated local ZIP backups and optional Google Drive integration.

Pi-Ready: Includes configuration for running as a background systemd service.

🛠️ Tech Stack

Backend: Python 3, Flask, Flask-SQLAlchemy (SQLite)

Frontend: Tailwind CSS, Lucide Icons

Deployment: Systemd (Linux/Raspberry Pi OS)

📦 Installation

Clone the repository:

git clone [https://github.com/selimsk/mastery-todo.git](https://github.com/YOUR_USERNAME/mastery-hub.git)

cd mastery-todo


Setup Virtual Environment:

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


Initialize Database:

python3 app.py


(The database and default routine will be created automatically on the first run.)

🔄 Automated Backups

To enable Google Drive backups:

Place your Google Service Account JSON file in the root directory.

Rename it to service_account.json.

The app will automatically sync backups every 7 days.

🖥️ Running as a Service (RPi)

To keep the app running after reboots, create a service file:
sudo nano /etc/systemd/system/mastery-todo.service

[Unit]
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/mastery-todo
ExecStart=/home/pi/mastery-todo/venv/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target


Run sudo systemctl enable mastery-todo && sudo systemctl start mastery-todo.

📄 License

MIT License - feel free to use and modify for personal or commercial use.
