from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class IFCFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False)
    processed = db.Column(db.Boolean, default=False)
    results = db.relationship('ProcessResult', backref='ifc_file', lazy=True)

class ProcessResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ifc_file_id = db.Column(db.Integer, db.ForeignKey('ifc_file.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    processing_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    material_data = db.Column(db.Text, nullable=False)  # JSON形式で材料データを保存

    def set_material_data(self, materials):
        self.material_data = json.dumps(materials)

    def get_material_data(self):
        return json.loads(self.material_data)