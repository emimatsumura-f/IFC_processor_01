from app import app

if __name__ == "__main__":
    # ホストを0.0.0.0に設定することで、ネットワーク上の他のマシンからもアクセス可能
    app.run(host="0.0.0.0", port=5000, debug=True)