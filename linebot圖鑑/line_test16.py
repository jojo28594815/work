import flask
from flask import request
import requests
import openai
import pymysql

# 設定 OpenAI API 密鑰
openai.api_key = "xxx"  # 替換為你的 OpenAI API 密鑰

# 建立 Flask 應用程式
app = flask.Flask(__name__)

# 設定 LINE Bot 的權杖與使用者 ID  # 替換為你的 LINE Bot 密鑰

auth_token = "xxx"
YouruserID = "xxx"

# 定義函式用來發送 LINE Bot 的回覆訊息
def LineText(replyToken, str1):
    global auth_token
    global YouruserID
    
    # 準備要發送的訊息內容
    message = {
        "replyToken": replyToken,
        "messages": [
            {
                "type": "text",
                "text": str1,
            }
        ]
    }

    # 設定 HTTP 標頭，加入 Authorization 欄位
    hed = {'Authorization': 'Bearer ' + auth_token}
    # LINE Bot API 的回覆訊息 URL
    url = 'https://api.line.me/v2/bot/message/reply'
    # 發送 POST 請求給 LINE API
    response = requests.post(url, json=message, headers=hed)
    return ""
#替換為你的 MySQL 資料庫
# 連接到 MySQL 資料庫
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='xxx',
        password='xxx',
        database='xxx'
    )

# 查詢最大編號的寶可夢
def get_max_pokemon():
    connection = get_db_connection()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM pokemon_info ORDER BY id DESC LIMIT 1"
            cursor.execute(sql)
            result = cursor.fetchone()
            if result:
                return {
                    'id': result['id'],
                    'name': result['name_zh']
                }
            else:
                return None
    finally:
        connection.close()

# 查詢特定編號的寶可夢
def get_pokemon_data(pokemon_id):
    connection = get_db_connection()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM pokemon_info WHERE id = %s"
            cursor.execute(sql, (pokemon_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'name': result['name_zh'],
                    'types': result['types_zh']
                }
            else:
                return None
    finally:
        connection.close()

# 定義責任鏈處理器基類
class Handler:
    def __init__(self, successor=None):
        self.successor = successor

    def handle(self, data):
        if self.successor:
            self.successor.handle(data)

# 定義處理 ChatGPT 請求的處理器
class ChatGPTHandler(Handler):
    def handle(self, data):
        if data['events'][0]['message']['type'] == 'text':
            user_message = data['events'][0]['message']['text']
            replyToken = data['events'][0]['replyToken']
            
            # 檢查是否是要求最大編號的寶可夢
            if "最大編號" in user_message:
                max_pokemon = get_max_pokemon()
                if max_pokemon:
                    reply_text = f"最大編號的寶可夢是 {max_pokemon['name']}，編號是 {max_pokemon['id']}。"
                else:
                    reply_text = "無法獲取寶可夢資料。"
            else:
                # 嘗試從用戶訊息中查詢寶可夢資料
                if user_message.isdigit():
                    pokemon_data = get_pokemon_data(int(user_message))
                    if pokemon_data:
                        reply_text = f"寶可夢資料:\n名稱: {pokemon_data['name']}\n類型: {pokemon_data['types']}"
                    else:
                        reply_text = "無法找到該編號的寶可夢。"
                else:
                    # 如果不是編號，則使用 ChatGPT 處理
                    try:
                        response = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "user", "content": user_message}
                            ]
                        )
                        chatgpt_reply = response.choices[0].message['content'].strip()
                        reply_text = chatgpt_reply
                    except Exception as e:
                        reply_text = f"Sorry, something went wrong: {e}"
                
            # 發送回應到 LINE Bot
            LineText(replyToken, reply_text)
        else:
            super().handle(data)

# 定義接收 POST 請求的路由
@app.route("/", methods=['POST'])
def LinePOST():
    try:
        data = request.json  # 獲取 POST 請求的 JSON 資料
        print(data)  # 印出接收到的資料
        
        # 設定責任鏈
        handler_chain = ChatGPTHandler()
        
        # 將請求資料傳遞給責任鏈進行處理
        handler_chain.handle(data)
        
        return ""
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Internal Server Error", 500

# 定義接收 GET 請求的路由
@app.route("/", methods=['GET'])
def hello():
    # 準備回應的 HTML 內容
    str1 = """
    <a href="http://127.0.0.1:5000/">http://127.0.0.1:5000/</a><br>
    歡迎訪問
    """
    return str1  # 回應內容

# 程式進入點
if __name__ == '__main__':
    # 啟動 Flask 伺服器，監聽 5000 埠
    app.run(port=5000)
