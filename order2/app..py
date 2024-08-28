from flask import Flask, render_template, request, redirect, url_for, Response
import cv2
import numpy as np
import os
import pickle
from datetime import datetime
import pymysql

app = Flask(__name__)

# 資料庫連線設定
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='bigup9',
        database='mode'
    )

# 訓練人臉辨識模型
def train_model():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = []
    labels = []
    label_map = {}
    label_id = 0

    # 從資料夾中讀取圖片
    for folder_name in os.listdir('faces'):
        folder_path = os.path.join('faces', folder_name)
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.jpg'):
                image_path = os.path.join(folder_path, file_name)
                image = cv2.imread(image_path)
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces.append(gray)
                labels.append(label_map.setdefault(folder_name, label_id))
                if folder_name not in label_map:
                    label_id += 1

    if faces:
        recognizer.train(faces, np.array(labels))
        recognizer.save('model.yml')
        with open('labels.pickle', 'wb') as f:
            pickle.dump(label_map, f)
    else:
        print("No faces found for training.")

# 簽到或簽退處理
def handle_sign_in_out(sign_type):
    if not os.path.exists('model.yml') or not os.path.exists('labels.pickle'):
        print("Model files are missing. Please train the model first.")
        return

    with open('labels.pickle', 'rb') as f:
        label_map = pickle.load(f)
    
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read('model.yml')

    cap = cv2.VideoCapture(0)
    identified_name = "Unknown"
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            roi_gray = gray_frame[y:y + h, x:x + w]
            id_, confidence = recognizer.predict(roi_gray)
            if confidence < 100:
                identified_name = [name for name, id_ in label_map.items() if id_ == id_][0]
        
        cv2.imshow('Video', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if identified_name != "Unknown":
        save_to_database(identified_name, sign_type)

# 保存簽到或簽退資料到資料庫
def save_to_database(user_name, sign_type):
    try:
        with get_db_connection() as db:
            with db.cursor() as cursor:
                if sign_type == 'sign_in':
                    sql = "INSERT INTO attendance (user_name, sign_in_time) VALUES (%s, NOW())"
                elif sign_type == 'sign_out':
                    sql = "UPDATE attendance SET sign_out_time = NOW() WHERE user_name = %s AND sign_out_time IS NULL"

                cursor.execute(sql, (user_name,))
                db.commit()
    except pymysql.MySQLError as e:
        print(f"Database error occurred: {e}")

# 新增使用者界面
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        if not user_name:
            return "User name is missing", 400
        try:
            with get_db_connection() as db:
                with db.cursor() as cursor:
                    cursor.execute("INSERT INTO users (username) VALUES (%s)", (user_name,))
                    db.commit()
        except pymysql.MySQLError as e:
            print(f"Database error occurred: {e}")

        return redirect(url_for('capture', user_name=user_name))

    return render_template('add_user.html')

# 網頁介面用來捕捉人臉並保存圖片
@app.route('/capture', methods=['GET','POST'])
def capture():
    user_name = request.args.get('user_name')  # 使用 request.args 來獲取 URL 參數
    if not user_name:
        return "User name is missing", 400
    
    if not os.path.exists(f'faces/{user_name}'):
        os.makedirs(f'faces/{user_name}')
    
    cap = cv2.VideoCapture(0)
    count = 0
    while count < 100:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.imshow('Capture Face', frame)

        # 按下 's' 鍵保存影像
        if cv2.waitKey(1) & 0xFF == ord('s'):
            cv2.imwrite(f'faces/{user_name}/{user_name}{count}.jpg', frame)
            count += 1

    cap.release()
    cv2.destroyAllWindows()

    # 訓練模型
    train_model()
    return redirect(url_for('index'))


# 主頁面，顯示簽到簽退紀錄
@app.route('/')
def index():
    try:
        with get_db_connection() as db:
            with db.cursor() as cursor:
                cursor.execute("SELECT * FROM attendance")
                records = cursor.fetchall()
    except pymysql.MySQLError as e:
        print(f"Database error occurred: {e}")
        records = []

    return render_template('index.html', records=records)

# 簽到/簽退處理
@app.route('/sign', methods=['POST'])
def sign():
    sign_type = request.form.get('sign_type')
    if sign_type not in ['sign_in', 'sign_out']:
        return "Invalid sign type", 400
    handle_sign_in_out(sign_type)
    return redirect(url_for('index'))

# 視頻流處理
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

if __name__ == '__main__':
    # 如果沒有模型，先訓練一個空模型
    if not os.path.exists('model.yml') or not os.path.exists('labels.pickle'):
        train_model()

    app.run(debug=True)
