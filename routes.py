import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from app import db, UPLOAD_FOLDER
from models import IFCFile, ProcessResult
from ifc_processor import IFCProcessor

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

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

        logger.info(f"Attempting to save file to: {filepath}")
        try:
            # ファイルを1MBのチャンクで効率的に読み書き
            CHUNK_SIZE = 1 * 1024 * 1024  # 1MB chunks
            with open(filepath, 'wb') as f:
                bytes_written = 0
                while True:
                    chunk = file.stream.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    f.flush()  # バッファをディスクに書き込む
                    bytes_written += len(chunk)

                logger.info(f"File saved successfully, total size: {bytes_written} bytes")

        except Exception as save_error:
            logger.error(f"Error saving file: {str(save_error)}", exc_info=True)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info("Cleaned up failed upload file")
                except Exception as remove_error:
                    logger.error(f"Error removing failed upload: {str(remove_error)}")
            return jsonify({'success': False, 'message': 'ファイルの保存中にエラーが発生しました。'})

        try:
            ifc_file = IFCFile(
                filename=filename,
                user_id=current_user.id,
                upload_date=datetime.utcnow()
            )
            db.session.add(ifc_file)
            db.session.commit()
            logger.info("File record created in database")
        except Exception as db_error:
            logger.error(f"Error creating database record: {str(db_error)}", exc_info=True)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info("Cleaned up file after database error")
                except Exception as remove_error:
                    logger.error(f"Error removing file after db failure: {str(remove_error)}")
            return jsonify({'success': False, 'message': 'データベースの更新中にエラーが発生しました。'})

        return jsonify({
            'success': True,
            'message': 'ファイルのアップロードが完了しました。',
            'progress': 100
        })
    except RequestEntityTooLarge:
        logger.error("File too large")
        return jsonify({'success': False, 'message': 'ファイルサイズが大きすぎます（上限: 200MB）。'})
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'エラーが発生しました: {str(e)}'})

@main_bp.route('/choice/material', methods=['POST'])
@login_required
def process_materials():
    try:
        logger.info("Starting material processing")
        # 最新の未処理ファイルを取得
        ifc_file = IFCFile.query.filter_by(
            user_id=current_user.id,
            processed=False
        ).order_by(IFCFile.upload_date.desc()).first()

        if not ifc_file:
            logger.warning("No unprocessed IFC file found")
            return jsonify({'success': False, 'message': 'IFCファイルが見つかりません。'}), 404

        filepath = os.path.join(UPLOAD_FOLDER, ifc_file.filename)
        if not os.path.exists(filepath):
            logger.error(f"IFC file not found at path: {filepath}")
            return jsonify({'success': False, 'message': 'ファイルが見つかりません。'}), 404

        logger.info(f"Processing IFC file: {filepath}")
        processor = IFCProcessor(filepath)

        try:
            materials = processor.extract_material_sizes()
            logger.info(f"Extracted {len(materials)} materials")

            # 材料情報をJSONシリアライズ可能な形式に変換
            materials_json = []
            for material in materials:
                material_dict = {}
                for key, value in material.items():
                    try:
                        if isinstance(value, (int, float)):
                            material_dict[key] = float(value)
                        elif isinstance(value, bool):
                            material_dict[key] = value
                        elif value is None:
                            material_dict[key] = None
                        else:
                            material_dict[key] = str(value)
                    except Exception as conv_error:
                        logger.warning(f"Error converting value for key {key}: {str(conv_error)}")
                        material_dict[key] = str(value)
                materials_json.append(material_dict)

            logger.debug(f"Converted materials to JSON: {materials_json[:2]}")  # 最初の2件のみログ出力

            # 処理結果を保存
            result = ProcessResult(
                ifc_file_id=ifc_file.id,
                user_id=current_user.id,
                processing_date=datetime.utcnow()
            )
            result.set_material_data(materials_json)

            ifc_file.processed = True
            db.session.add(result)
            db.session.commit()
            logger.info("Processing results saved to database")

            response = jsonify({
                'success': True,
                'materials': materials_json,
                'message': '材料集計が完了しました。'
            })
            response.headers['Content-Type'] = 'application/json'
            return response

        except ValueError as ve:
            logger.error(f"Value error during processing: {str(ve)}")
            return jsonify({
                'success': False,
                'message': f'データ処理エラー: {str(ve)}'
            }), 400
        except Exception as e:
            logger.error(f"Unexpected error during processing: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': '処理中に予期せぬエラーが発生しました。'
            }), 500

    except Exception as e:
        logger.error(f"Error during material processing: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'エラーが発生しました: {str(e)}'
        }), 500

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