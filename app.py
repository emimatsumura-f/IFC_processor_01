import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.ext.declarative import declarative_base

# プロジェクトのルートディレクトリを取得
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# アップロードフォルダの作成
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

Base = declarative_base()
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get("SESSION_SECRET", "your-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    f'sqlite:///{os.path.join(BASE_DIR, "instance", "app.db")}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'ログインしてください。'

# User loader callback
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    import models
    db.create_all()

    from auth import auth_bp
    from routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)