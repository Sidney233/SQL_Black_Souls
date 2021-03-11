from flask import Flask
from flask_apscheduler import APScheduler

from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import psycopg2
app = Flask(__name__)
app.config.from_object(Config)
conn = psycopg2.connect(database="black_souls", user="postgres", password="123456", host="localhost", port="5432")
cursor = conn.cursor()
login = LoginManager(app)
login.login_view = 'login'
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
from app import routes, models
