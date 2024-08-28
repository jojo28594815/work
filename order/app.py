from flask import Flask, render_template, request, redirect, url_for
import pymysql
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from datetime import datetime

app = Flask(__name__)

# 資料庫連接設定
db = pymysql.connect(host='localhost', user='pi', password='raspberry', database='rfid_db')
cursor = db.cursor()

# 設定RFID模組
reader = SimpleMFRC522()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        query = """SELECT al.id, ch.user_name, al.login_time, al.logout_time 
                   FROM access_log al 
                   JOIN cardholders ch ON al.card_uid = ch.card_uid
                   WHERE al.login_time >= %s AND al.logout_time <= %s"""
        cursor.execute(query, (start_time, end_time))
        logs = cursor.fetchall()
    else:
        query = """SELECT al.id, ch.user_name, al.login_time, al.logout_time 
                   FROM access_log al 
                   JOIN cardholders ch ON al.card_uid = ch.card_uid"""
        cursor.execute(query)
        logs = cursor.fetchall()

    return render_template('index.html', logs=logs)

@app.route('/add_cardholder', methods=['GET', 'POST'])
def add_cardholder():
    if request.method == 'POST':
        user_name = request.form['user_name']
        
        # 讀取卡片UID
        print("請將卡片靠近讀取器...")
        card_uid = reader.read_id()
        
        # 插入卡片持有者資料
        cursor.execute("INSERT INTO cardholders (card_uid, user_name) VALUES (%s, %s)", (card_uid, user_name))
        db.commit()
        
        return redirect(url_for('success'))
    
    return render_template('add_cardholder.html')

@app.route('/success')
def success():
    return "卡片持有者資料已成功寫入！"

@app.route('/log_access')
def log_access():
    try:
        print("請將卡片靠近讀取器...")
        card_uid = reader.read_id()

        # 檢查卡片是否在持有者名單中
        cursor.execute("SELECT user_name FROM cardholders WHERE card_uid = %s", (card_uid,))
        cardholder = cursor.fetchone()

        if cardholder:
            cursor.execute("SELECT * FROM access_log WHERE card_uid = %s ORDER BY id DESC LIMIT 1", (card_uid,))
            result = cursor.fetchone()

            if result and result[3] is None:
                # 若有登入記錄且尚未登出，則更新登出時間
                logout_time = datetime.now()
                cursor.execute("UPDATE access_log SET logout_time = %s WHERE id = %s", (logout_time, result[0]))
                db.commit()
                message = f"{cardholder[0]} 登出成功！"
            else:
                # 創建新登入記錄
                login_time = datetime.now()
                cursor.execute("INSERT INTO access_log (card_uid, login_time) VALUES (%s, %s)", (card_uid, login_time))
                db.commit()
                message = f"{cardholder[0]} 登入成功！"
        else:
            message = "未註冊的卡片！"

        # 返回帶有自動跳轉的 HTML 回應
        return f"""
        <html>
            <head>
                <meta http-equiv="refresh" content="5;url=/" />
            </head>
            <body>
                <h1>{message}</h1>
                <p>5秒後將自動返回首頁...</p>
            </body>
        </html>
        """
    
    finally:
        GPIO.cleanup()
@app.route('/edit_cardholder', methods=['GET', 'POST'])
def edit_cardholder():
    if request.method == 'POST':
        # 從表單接收資料
        card_uid = request.form['card_uid']
        new_name = request.form['new_name']

        # 更新卡片持有者名稱
        cursor.execute("UPDATE cardholders SET user_name = %s WHERE card_uid = %s", (new_name, card_uid))
        db.commit()

        message = "卡片持有者名稱已成功修改！"

        # 返回帶有自動跳轉的 HTML 回應
        return f"""
        <html>
            <head>
                <meta http-equiv="refresh" content="5;url=/" />
            </head>
            <body>
                <h1>{message}</h1>
                <p>5秒後將自動返回首頁...</p>
            </body>
        </html>
        """
    else:
        # 從資料庫中獲取所有卡片持有者資料
        cursor.execute("SELECT card_uid, user_name FROM cardholders")
        cardholders = cursor.fetchall()

        # 渲染編輯持有者名稱的頁面
        return render_template('edit_cardholder.html', cardholders=cardholders)


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0',debug=True,port=5000)
    finally:
        db.close()
