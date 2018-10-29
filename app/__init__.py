from celery import Celery
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'SuperRandomSecretKeyNotPassedByEnv...'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

celery = Celery(
    'tasks',
    backend=app.config['CELERY_RESULT_BACKEND'],
    broker=app.config['CELERY_BROKER_URL']
)
celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    task_routes={'split_video': {'queue': 'server'},
                 'infer_from_video': {'queue': 'inference'}
                }
)

from app import views
