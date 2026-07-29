from django.shortcuts import get_object_or_404
from django.http import Http404
from ..models import Master

def get_master_by_identifier(identifier):
    """
    Находит мастера по логину или ID (если строка начинается с 'id')
    
    Args:
        identifier (str): логин или 'id<число>'
    
    Returns:
        Master: объект мастера
    
    Raises:
        Http404: если мастер не найден
    """
    if not identifier:
        raise Http404("Идентификатор мастера не указан")
    
    if identifier.startswith('id'):
        try:
            master_id = int(identifier[2:])
            return get_object_or_404(Master, id=master_id)
        except ValueError:
            raise Http404("Неверный ID мастера")
    else:
        return get_object_or_404(Master, login=identifier)