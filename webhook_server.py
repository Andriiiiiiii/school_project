# Создать файл webhook_server.py
from flask import Flask, request, jsonify
import json
from services.payment import PaymentService
from database import crud

app = Flask(__name__)

@app.route('/yookassa-webhook', methods=['POST'])
def yookassa_webhook():
    try:
        data = request.get_json()
        result = PaymentService.process_webhook(data)
        
        if result and result.get('success'):
            chat_id = result['chat_id']
            payment_id = result['payment_id']
            
            # Активируем подписку
            expiry_date = PaymentService.calculate_subscription_expiry()
            crud.update_user_subscription(chat_id, "premium", expiry_date, payment_id)
            
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)