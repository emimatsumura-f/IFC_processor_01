import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from models import IFCFile
from ifc_processor import IFCProcessor

main_bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@main_bp.route('/')
@main_bp.route('/main')
@login_required
def index():
    return render_template('main.html')

@main_bp.route('/upload/ifc', methods=['POST'])
@login_required
def upload_ifc():
    if 'ifc_file' not in request.files:
        return jsonify({'success': False, 'message': 'ファイルが選択されていません。'})
    
    file = request.files['ifc_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'ファイルが選択されていません。'})
    
    if not file.filename.endswith('.ifc'):
        return jsonify({'success': False, 'message': 'IFCファイルのみアップロード可能です。'})
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        ifc_file = IFCFile(
            filename=filename,
            user_id=current_user.id,
            upload_date=datetime.utcnow()
        )
        db.session.add(ifc_file)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@main_bp.route('/choice/material', methods=['POST'])
@login_required
def process_materials():
    try:
        ifc_file = IFCFile.query.filter_by(
            user_id=current_user.id,
            processed=False
        ).order_by(IFCFile.upload_date.desc()).first()
        
        if not ifc_file:
            return jsonify({'success': False, 'message': 'IFCファイルが見つかりません。'})
        
        filepath = os.path.join(UPLOAD_FOLDER, ifc_file.filename)
        processor = IFCProcessor(filepath)
        materials = processor.extract_material_sizes()
        
        ifc_file.processed = True
        db.session.commit()
        
        return jsonify({'success': True, 'materials': materials})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@main_bp.route('/download/csv', methods=['POST'])
@login_required
def download_csv():
    try:
        ifc_file = IFCFile.query.filter_by(
            user_id=current_user.id,
            processed=True
        ).order_by(IFCFile.upload_date.desc()).first()
        
        if not ifc_file:
            return 'ファイルが見つかりません。', 404
        
        filepath = os.path.join(UPLOAD_FOLDER, ifc_file.filename)
        processor = IFCProcessor(filepath)
        materials = processor.extract_material_sizes()
        csv_data = processor.generate_csv(materials)
        
        return csv_data, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=material_list.csv'
        }
    except Exception as e:
        return str(e), 500
