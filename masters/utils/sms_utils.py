import requests
import os

def send_sms(phone, code):
    """Отправляет SMS с кодом подтверждения через SMS.ru"""
    api_key = os.getenv('SMS_API_KEY')
    sender = os.getenv('SMS_SENDER', 'DATY')
    
    # Убираем лишние символы из номера
    phone_cleaned = phone.replace('+', '').replace(' ', '').replace('-', '')
    
    url = "https://sms.ru/sms/send"
    params = {
        'api_id': api_key,
        'to': phone_cleaned,
        'msg': f'Код подтверждения: {code}',
        'json': 1,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        # Проверяем статус ответа
        if result.get('status_code') == 100:
            print(f"SMS отправлено на {phone}: {code}")
            return True, result
        else:
            print(f"Ошибка отправки SMS: {result}")
            return False, result
    except Exception as e:
        print(f"Ошибка при отправке SMS: {e}")
        return False, {'error': str(e)}