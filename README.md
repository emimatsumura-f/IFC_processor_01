# IFC Converter

IFCファイルから構造部材の材料集計データを抽出し、解析と可視化を行うWebアプリケーション。

## 機能

- IFCファイルのアップロードと解析
- 構造部材の材料情報の抽出
- 材料集計結果のCSVエクスポート
- 過去の処理結果の閲覧

## 技術スタック

- Python 3.8
- Flask 2.0.1
- SQLAlchemy 1.4.41
- IfcOpenShell
- Bootstrap 5

## ローカル環境でのセットアップ

1. リポジトリのクローン:
```bash
git clone <your-repository-url>
cd ifc-converter
```

2. Python 3.8の仮想環境を作成してアクティベート:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

3. 必要なパッケージのインストール:
```bash
pip install flask==2.0.1 \
    flask-login==0.5.0 \
    flask-sqlalchemy==2.5.1 \
    flask-wtf==0.15.1 \
    gunicorn==20.1.0 \
    ifcopenshell \
    psycopg2-binary \
    sqlalchemy==1.4.41 \
    werkzeug==2.0.3 \
    email-validator
```

4. 必要なディレクトリの作成:
```bash
mkdir -p uploads instance
```

5. 環境変数の設定:
```bash
# Windows:
set SESSION_SECRET=your-secret-key
# macOS/Linux:
export SESSION_SECRET=your-secret-key
```

6. アプリケーションの起動:
```bash
# 開発モード
python main.py

# または本番モード
gunicorn --bind 0.0.0.0:5000 main:app
```

## プロジェクト構造

```
ifc-converter/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── auth.py
│   └── ifc_processor.py
├── static/
│   ├── css/
│   │   └── custom.css
│   └── js/
│       └── upload.js
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── main.html
│   ├── results.html
│   ├── signup.html
│   └── result_detail.html
├── uploads/
│   └── .gitkeep
├── instance/
│   └── .gitkeep
├── .gitignore
├── app.py
├── main.py
└── requirements.txt
```

## 注意事項

- `uploads/` ディレクトリにアップロードされたIFCファイルが保存されます
- `instance/` ディレクトリにSQLiteデータベースファイルが作成されます
- 環境変数 `SESSION_SECRET` を必ず設定してください

## ライセンス

MIT License
