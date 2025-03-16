import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from models import IFCFile, ProcessResult
from ifc_processor import IFCProcessor

main_bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@main_bp.route('/')
@main_bp.route('/main')
@login_required
def index():
    # 最近の処理結果を取得
    recent_results = ProcessResult.query.filter_by(
        user_id=current_user.id
    ).order_by(ProcessResult.processing_date.desc()).limit(5).all()
    return render_template('main.html', recent_results=recent_results)

@main_bp.route('/upload/ifc', methods=['POST'])
@login_required
def upload_ifc():
    try:
        if 'ifc_file' not in request.files:
            return jsonify({'success': False, 'message': 'ファイルが選択されていません。'})

        file = request.files['ifc_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'ファイルが選択されていません。'})

        if not file.filename.endswith('.ifc'):
            return jsonify({'success': False, 'message': 'IFCファイルのみアップロード可能です。'})

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # 既存のファイルを確認し、必要に応じて名前を変更
        base_name = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1]
        counter = 1
        while os.path.exists(filepath):
            filename = f"{base_name}_{counter}{extension}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            counter += 1

        file.save(filepath)

        ifc_file = IFCFile(
            filename=filename,
            user_id=current_user.id,
            upload_date=datetime.utcnow()
        )
        db.session.add(ifc_file)
        db.session.commit()

        return jsonify({'success': True, 'message': 'ファイルのアップロードが完了しました。'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'エラーが発生しました: {str(e)}'})

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

        # 処理結果を保存
        result = ProcessResult(
            ifc_file_id=ifc_file.id,
            user_id=current_user.id
        )
        result.set_material_data(materials)

        ifc_file.processed = True
        db.session.add(result)
        db.session.commit()

        return jsonify({'success': True, 'materials': materials})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@main_bp.route('/results')
@login_required
def view_results():
    results = ProcessResult.query.filter_by(
        user_id=current_user.id
    ).order_by(ProcessResult.processing_date.desc()).all()
    return render_template('results.html', results=results)

@main_bp.route('/results/<int:result_id>')
@login_required
def view_result(result_id):
    result = ProcessResult.query.filter_by(
        id=result_id,
        user_id=current_user.id
    ).first_or_404()
    return render_template('result_detail.html', result=result)

@main_bp.route('/download/csv', methods=['POST'])
@login_required
def download_csv():
    try:
        result_id = request.form.get('result_id')
        if result_id:
            # 保存された結果からCSVを生成
            result = ProcessResult.query.get_or_404(result_id)
            materials = result.get_material_data()
        else:
            # 最新の処理済みファイルからCSVを生成
            ifc_file = IFCFile.query.filter_by(
                user_id=current_user.id,
                processed=True
            ).order_by(IFCFile.upload_date.desc()).first()

            if not ifc_file:
                return 'ファイルが見つかりません。', 404

            filepath = os.path.join(UPLOAD_FOLDER, ifc_file.filename)
            processor = IFCProcessor(filepath)
            materials = processor.extract_material_sizes()

        processor = IFCProcessor(None)  # CSVジェネレーターのみ使用
        csv_data = processor.generate_csv(materials)

        return csv_data, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=material_list.csv'
        }
    except Exception as e:
        return str(e), 500