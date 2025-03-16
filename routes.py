import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from models import IFCFile, ProcessResult
from ifc_processor import IFCProcessor

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    logger.info(f"Created upload folder: {UPLOAD_FOLDER}")

@main_bp.route('/')
@main_bp.route('/main')
@login_required
def index():
    recent_results = ProcessResult.query.filter_by(
        user_id=current_user.id
    ).order_by(ProcessResult.processing_date.desc()).limit(5).all()
    return render_template('main.html', recent_results=recent_results)

@main_bp.route('/upload/ifc', methods=['POST'])
@login_required
def upload_ifc():
    try:
        if 'ifc_file' not in request.files:
            logger.warning("No file part in request")
            return jsonify({'success': False, 'message': 'ファイルが選択されていません。'})

        file = request.files['ifc_file']
        if file.filename == '':
            logger.warning("No selected file")
            return jsonify({'success': False, 'message': 'ファイルが選択されていません。'})

        if not file.filename.endswith('.ifc'):
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({'success': False, 'message': 'IFCファイルのみアップロード可能です。'})

        # アップロードフォルダの確認と作成
        if not os.path.exists(UPLOAD_FOLDER):
            logger.info("Creating upload folder")
            os.makedirs(UPLOAD_FOLDER)

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

        logger.info(f"Saving file to: {filepath}")
        file.save(filepath)
        logger.info("File saved successfully")

        ifc_file = IFCFile(
            filename=filename,
            user_id=current_user.id,
            upload_date=datetime.utcnow()
        )
        db.session.add(ifc_file)
        db.session.commit()
        logger.info("File record created in database")

        return jsonify({'success': True, 'message': 'ファイルのアップロードが完了しました。'})
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'エラーが発生しました: {str(e)}'})

@main_bp.route('/choice/material', methods=['POST'])
@login_required
def process_materials():
    try:
        logger.info("Starting material processing")
        ifc_file = IFCFile.query.filter_by(
            user_id=current_user.id,
            processed=False
        ).order_by(IFCFile.upload_date.desc()).first()

        if not ifc_file:
            logger.warning("No unprocessed IFC file found")
            return jsonify({'success': False, 'message': 'IFCファイルが見つかりません。'})

        filepath = os.path.join(UPLOAD_FOLDER, ifc_file.filename)
        if not os.path.exists(filepath):
            logger.error(f"IFC file not found at path: {filepath}")
            return jsonify({'success': False, 'message': 'ファイルが見つかりません。'})

        logger.info(f"Processing IFC file: {filepath}")
        processor = IFCProcessor(filepath)
        materials = processor.extract_material_sizes()
        logger.info(f"Extracted {len(materials)} materials")

        # 処理結果を保存
        result = ProcessResult(
            ifc_file_id=ifc_file.id,
            user_id=current_user.id
        )
        result.set_material_data(materials)

        ifc_file.processed = True
        db.session.add(result)
        db.session.commit()
        logger.info("Processing results saved to database")

        return jsonify({'success': True, 'materials': materials})
    except Exception as e:
        logger.error(f"Error during material processing: {str(e)}", exc_info=True)
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
        logger.error(f"Error during CSV download: {str(e)}", exc_info=True)
        return str(e), 500