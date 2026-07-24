from django.http import JsonResponse

def api_response(success, data=None, error=None, status=200):
    """
    Универсальный формат ответа API
    
    Args:
        success (bool): Успешно ли выполнена операция
        data (dict, optional): Данные для передачи
        error (str, optional): Сообщение об ошибке
        status (int): HTTP статус код
    
    Returns:
        JsonResponse: Ответ в едином формате
    """
    response = {'success': success}
    
    if data is not None:
        response['data'] = data
    
    if error is not None:
        response['error'] = error
    
    return JsonResponse(response, status=status)

def api_success(data=None, status=200):
    """
    Ответ с успехом
    """
    return api_response(True, data=data, status=status)

def api_error(error, status=400, data=None):
    """
    Ответ с ошибкой
    """
    return api_response(False, data=data, error=error, status=status)