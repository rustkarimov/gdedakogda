from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth import logout as auth_logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Master, Service, Booking, Schedule, DayOff, PhoneVerification, CustomUser, Break, ExtraWorkingDay, ExtraWorkingDayBreak, ServiceCategory
from .forms import PhoneRegistrationForm, PhoneVerificationForm

from django.views.decorators.http import require_http_methods
from .models import ExtraWorkingDay, ExtraWorkingDayBreak


from .utils.schedule_utils import ScheduleCalculator
from datetime import datetime, timedelta, date
import random
import json


def get_weekday_ru(date_obj):
    weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return weekdays[date_obj.weekday()]

def get_month_ru(date_obj):
    months = [
        'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]
    return months[date_obj.month - 1]



# Главная страница
def home(request):
    return render(request, 'masters/public/index.html')

# Личный кабинет
@login_required
def dashboard(request):
    try:
        master = request.user.master
    except Master.DoesNotExist:
        master = Master.objects.create(user=request.user)
    
    total_bookings = Booking.objects.filter(master=master).count()
    upcoming_bookings = Booking.objects.filter(
        master=master, 
        status='confirmed'
    ).order_by('date', 'time')[:5]
    
    total_services = Service.objects.filter(master=master).count()
    
    context = {
        'master': master,
        'total_bookings': total_bookings,
        'upcoming_bookings': upcoming_bookings,
        'total_services': total_services,
    }
    return render(request, 'masters/dashboard.html', context)

@login_required
def get_calendar_schedule(request):
    """API для получения расписания мастера для календаря (с учетом доп. дней)"""
    master = request.user.master
    
    # Получаем регулярное расписание
    schedules = Schedule.objects.filter(master=master)
    schedules_data = {}
    for schedule in schedules:
        schedules_data[schedule.day_of_week] = {
            'start': schedule.start_time.strftime('%H:%M'),
            'end': schedule.end_time.strftime('%H:%M'),
            'breaks': [{
                'start': b.start_time.strftime('%H:%M'),
                'end': b.end_time.strftime('%H:%M')
            } for b in schedule.breaks.all()]
        }
    
    # Получаем выходные дни
    days_off = DayOff.objects.filter(
        master=master,
        date__gte=date.today()
    ).values_list('date', flat=True)
    days_off_list = [d.strftime('%Y-%m-%d') for d in days_off]
    
    # Получаем дополнительные рабочие дни
    extra_days = ExtraWorkingDay.objects.filter(
        master=master,
        date__gte=date.today()
    )
    extra_days_data = {}
    for day in extra_days:
        extra_days_data[day.date.strftime('%Y-%m-%d')] = {
            'start': day.start_time.strftime('%H:%M'),
            'end': day.end_time.strftime('%H:%M'),
            'breaks': [{
                'start': b.start_time.strftime('%H:%M'),
                'end': b.end_time.strftime('%H:%M')
            } for b in day.breaks.all()]
        }
    
    return JsonResponse({
        'schedules': schedules_data,
        'days_off': days_off_list,
        'extra_days': extra_days_data
    })


@login_required
def get_bookings_api(request):
    """API для получения записей с пагинацией"""
    master = request.user.master
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))
    offset = (page - 1) * limit
    
    bookings = Booking.objects.filter(
        master=master,
        status='confirmed'
    ).order_by('date', 'time')
    
    total = bookings.count()
    has_more = offset + limit < total
    
    bookings_page = bookings[offset:offset + limit]
    
    data = []
    for booking in bookings_page:
        data.append({
            'id': booking.id,
            'date': booking.date.strftime('%d.%m.%Y'),
            'time': booking.time.strftime('%H:%M'),
            'client_name': booking.client_name,
            'service_name': booking.service.name,
        })
    
    return JsonResponse({
        'bookings': data,
        'total': total,
        'page': page,
        'has_more': has_more
    })



# Профиль
@login_required
def profile(request):
    try:
        master = request.user.master
    except Master.DoesNotExist:
        master = Master.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Обновляем данные мастера
        master.phone = request.POST.get('phone', '')
        master.first_name = request.POST.get('first_name', '')
        master.last_name = request.POST.get('last_name', '')
        master.bio = request.POST.get('bio', '')
        
        # Обновляем логин
        new_login = request.POST.get('login', '').strip()
        if new_login != (master.login or ''):
            # Валидация логина
            import re
            if new_login:
                if len(new_login) < 3:
                    messages.error(request, 'Логин должен содержать минимум 3 символа')
                    return redirect('profile')
                if not re.match(r'^[a-zA-Z0-9_-]+$', new_login):
                    messages.error(request, 'Логин может содержать только латиницу, цифры, дефис и подчеркивание')
                    return redirect('profile')
                if Master.objects.exclude(pk=master.pk).filter(login=new_login).exists():
                    messages.error(request, 'Этот логин уже занят')
                    return redirect('profile')
                master.login = new_login
            else:
                master.login = None
            messages.success(request, 'Логин сохранен! Ваша ссылка обновлена.')
        
        master.save()
        
        # Обновляем имя в User (только first_name и last_name)
        user = request.user
        user.first_name = master.first_name
        user.last_name = master.last_name
        user.save()
        
        messages.success(request, 'Профиль обновлен!')
        return redirect('profile')
    
    return render(request, 'masters/profile.html', {'master': master})


@login_required
def schedule(request):
    """Настройка регулярного расписания (AJAX версия)"""
    master = request.user.master
    schedules = Schedule.objects.filter(master=master).order_by('day_of_week')
    
    return render(request, 'masters/schedule.html', {
        'schedules': schedules,
    })


# +++++++++++++++++++  УСЛУГИ  +++++++++++++++++

@login_required
def services(request):
    """Страница управления услугами"""
    master = request.user.master
    services_list = Service.objects.filter(master=master)
    return render(request, 'masters/services.html', {'services': services_list})

@login_required
@require_http_methods(["POST"])
def api_add_service(request):
    master = request.user.master
    data = json.loads(request.body)
    
    category_id = data.get('category_id')
    category = None
    if category_id:
        category = get_object_or_404(ServiceCategory, id=category_id, master=master)
    
    service = Service.objects.create(
        master=master,
        category=category,
        name=data.get('name'),
        description=data.get('description', ''),
        duration=data.get('duration'),
        price=data.get('price'),
        is_active=data.get('is_active', True)
    )
    return JsonResponse({'success': True, 'service_id': service.id})

@login_required
@require_http_methods(["POST"])
def api_edit_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, master=request.user.master)
    data = json.loads(request.body)
    
    category_id = data.get('category_id')
    category = None
    if category_id:
        category = get_object_or_404(ServiceCategory, id=category_id, master=request.user.master)
    
    service.category = category
    service.name = data.get('name')
    service.description = data.get('description', '')
    service.duration = data.get('duration')
    service.price = data.get('price')
    service.is_active = data.get('is_active', True)
    service.save()
    
    return JsonResponse({'success': True})

@login_required
@require_http_methods(["POST"])
def api_delete_service(request, service_id):
    """API удаления услуги"""
    service = get_object_or_404(Service, id=service_id, master=request.user.master)
    service.delete()
    
    return JsonResponse({'success': True})


@login_required
def get_categories(request):
    """API для получения категорий с услугами"""
    master = request.user.master
    categories = ServiceCategory.objects.filter(master=master, is_active=True)
    
    # Получаем услуги без категории
    uncategorized = Service.objects.filter(master=master, category__isnull=True, is_active=True)
    
    data = []
    for cat in categories:
        services = Service.objects.filter(master=master, category=cat, is_active=True)
        data.append({
            'id': cat.id,
            'name': cat.name,
            'order': cat.order,
            'services': [{
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'duration': s.duration,
                'price': float(s.price)
            } for s in services]
        })
    
    return JsonResponse({
        'categories': data,
        'uncategorized': [{
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'duration': s.duration,
            'price': float(s.price)
        } for s in uncategorized]
    })

@login_required
@require_http_methods(["POST"])
def api_add_category(request):
    master = request.user.master
    data = json.loads(request.body)
    
    category = ServiceCategory.objects.create(
        master=master,
        name=data.get('name'),
        order=data.get('order', 0)
    )
    return JsonResponse({'success': True, 'id': category.id})

@login_required
@require_http_methods(["POST"])
def api_edit_category(request, category_id):
    category = get_object_or_404(ServiceCategory, id=category_id, master=request.user.master)
    data = json.loads(request.body)
    
    category.name = data.get('name')
    category.order = data.get('order', 0)
    category.save()
    return JsonResponse({'success': True})

@login_required
@require_http_methods(["POST"])
def api_delete_category(request, category_id):
    category = get_object_or_404(ServiceCategory, id=category_id, master=request.user.master)
    # Услуги остаются, категория становится null
    Service.objects.filter(category=category).update(category=None)
    category.delete()
    return JsonResponse({'success': True})

@login_required
def api_get_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, master=request.user.master)
    return JsonResponse({
        'id': service.id,
        'name': service.name,
        'description': service.description,
        'duration': service.duration,
        'price': float(service.price),
        'is_active': service.is_active,
        'category_id': service.category_id
    }) 

def get_master_categories(request, login):
    """API для получения категорий конкретного мастера по логину"""
    master = get_object_or_404(Master, login=login)
    categories = ServiceCategory.objects.filter(master=master, is_active=True)
    
    # Получаем услуги без категории
    uncategorized = Service.objects.filter(master=master, category__isnull=True, is_active=True)
    
    data = []
    for cat in categories:
        services = Service.objects.filter(master=master, category=cat, is_active=True)
        data.append({
            'id': cat.id,
            'name': cat.name,
            'order': cat.order,
            'services': [{
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'duration': s.duration,
                'price': float(s.price)
            } for s in services]
        })
    
    return JsonResponse({
        'categories': data,
        'uncategorized': [{
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'duration': s.duration,
            'price': float(s.price)
        } for s in uncategorized]
    }) 


@login_required
def delete_schedule(request, schedule_id):
    """Удаление расписания"""
    schedule = get_object_or_404(Schedule, id=schedule_id, master=request.user.master)
    schedule.delete()
    messages.success(request, 'Расписание удалено')
    return redirect('schedule')

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@login_required
@require_http_methods(["POST"])
def api_add_schedule(request):
    """API добавления расписания"""
    master = request.user.master
    data = json.loads(request.body)
    
    day_of_week = data.get('day_of_week')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    breaks = data.get('breaks', [])
    
    # Проверяем, не существует ли уже
    if Schedule.objects.filter(master=master, day_of_week=day_of_week).exists():
        return JsonResponse({'error': 'Расписание для этого дня уже существует'}, status=400)
    
    # Создаем расписание
    schedule = Schedule.objects.create(
        master=master,
        day_of_week=day_of_week,
        start_time=datetime.strptime(start_time, '%H:%M').time(),
        end_time=datetime.strptime(end_time, '%H:%M').time()
    )
    
    # Добавляем перерывы
    for break_data in breaks:
        if break_data.get('start') and break_data.get('end'):
            Break.objects.create(
                schedule=schedule,
                start_time=datetime.strptime(break_data['start'], '%H:%M').time(),
                end_time=datetime.strptime(break_data['end'], '%H:%M').time()
            )
    
    return JsonResponse({
        'success': True,
        'message': 'Расписание добавлено',
        'schedule': {
            'id': schedule.id,
            'day_of_week': schedule.day_of_week,
            'day_name': schedule.get_day_of_week_display(),
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'breaks': [{
                'start': b.start_time.strftime('%H:%M'),
                'end': b.end_time.strftime('%H:%M')
            } for b in schedule.breaks.all()]
        }
    })

@login_required
@require_http_methods(["POST"])
def api_edit_schedule(request, schedule_id):
    """API редактирования расписания"""
    schedule = get_object_or_404(Schedule, id=schedule_id, master=request.user.master)
    data = json.loads(request.body)
    
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    breaks = data.get('breaks', [])
    
    # Обновляем основные часы
    if start_time and end_time:
        schedule.start_time = datetime.strptime(start_time, '%H:%M').time()
        schedule.end_time = datetime.strptime(end_time, '%H:%M').time()
        schedule.save()
    
    # Обновляем перерывы
    schedule.breaks.all().delete()
    for break_data in breaks:
        if break_data.get('start') and break_data.get('end'):
            Break.objects.create(
                schedule=schedule,
                start_time=datetime.strptime(break_data['start'], '%H:%M').time(),
                end_time=datetime.strptime(break_data['end'], '%H:%M').time()
            )
    
    return JsonResponse({
        'success': True,
        'message': 'Расписание обновлено',
        'schedule': {
            'id': schedule.id,
            'day_of_week': schedule.day_of_week,
            'day_name': schedule.get_day_of_week_display(),
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'breaks': [{
                'start': b.start_time.strftime('%H:%M'),
                'end': b.end_time.strftime('%H:%M')
            } for b in schedule.breaks.all()]
        }
    })

@login_required
@require_http_methods(["POST"])
def api_delete_schedule(request, schedule_id):
    """API удаления расписания"""
    schedule = get_object_or_404(Schedule, id=schedule_id, master=request.user.master)
    schedule.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Расписание удалено'
    })



@login_required
def get_extra_days(request):
    """API для получения дополнительных рабочих дней"""
    master = request.user.master
    extra_days = ExtraWorkingDay.objects.filter(master=master).order_by('-date')
    
    data = []
    for day in extra_days:
        data.append({
            'id': day.id,
            'date': day.date.strftime('%Y-%m-%d'),
            'date_display': day.date.strftime('%d.%m.%Y'),
            'weekday': day.date.strftime('%A'),
            'start_time': day.start_time.strftime('%H:%M'),
            'end_time': day.end_time.strftime('%H:%M'),
            'breaks': [{
                'start': b.start_time.strftime('%H:%M'),
                'end': b.end_time.strftime('%H:%M')
            } for b in day.breaks.all()]
        })
    
    return JsonResponse({'extra_days': data})

@login_required
@require_http_methods(["POST"])
def api_add_extra_day(request):
    """API добавления дополнительного рабочего дня"""
    master = request.user.master
    data = json.loads(request.body)
    
    date_str = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    breaks = data.get('breaks', [])
    
    if not date_str or not start_time or not end_time:
        return JsonResponse({'error': 'Заполните все обязательные поля'}, status=400)
    
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Проверяем, не существует ли уже
    if ExtraWorkingDay.objects.filter(master=master, date=target_date).exists():
        return JsonResponse({'error': 'Этот день уже добавлен'}, status=400)
    
    # Создаем дополнительный рабочий день
    extra_day = ExtraWorkingDay.objects.create(
        master=master,
        date=target_date,
        start_time=datetime.strptime(start_time, '%H:%M').time(),
        end_time=datetime.strptime(end_time, '%H:%M').time()
    )
    
    # Добавляем перерывы
    for break_data in breaks:
        if break_data.get('start') and break_data.get('end'):
            ExtraWorkingDayBreak.objects.create(
                extra_day=extra_day,
                start_time=datetime.strptime(break_data['start'], '%H:%M').time(),
                end_time=datetime.strptime(break_data['end'], '%H:%M').time()
            )
    
    return JsonResponse({
        'success': True,
        'message': 'Дополнительный рабочий день добавлен'
    })

@login_required
@require_http_methods(["POST"])
def api_delete_extra_day(request, extra_day_id):
    """API удаления дополнительного рабочего дня"""
    extra_day = get_object_or_404(ExtraWorkingDay, id=extra_day_id, master=request.user.master)
    extra_day.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Дополнительный рабочий день удален'
    })


@login_required
def get_extra_days_list(request):
    master = request.user.master
    extra_days = ExtraWorkingDay.objects.filter(master=master)
    
    data = []
    for day in extra_days:
        data.append({
            'id': day.id,
            'date': day.date.strftime('%Y-%m-%d'),
            'start': day.start_time.strftime('%H:%M'),
            'end': day.end_time.strftime('%H:%M'),
            'breaks': [{
                'start': b.start_time.strftime('%H:%M'),
                'end': b.end_time.strftime('%H:%M')
            } for b in day.breaks.all()]
        })
    
    return JsonResponse({'extra_days': data})

@login_required
def get_days_off_list(request):
    """API для получения списка выходных дней"""
    master = request.user.master
    days_off = DayOff.objects.filter(master=master).order_by('-date')
    
    data = []
    for day in days_off:
        data.append({
            'id': day.id,
            'date': day.date.strftime('%Y-%m-%d'),
            'date_display': day.date.strftime('%d.%m.%Y'),
            'weekday': day.date.strftime('%A'),
            'reason': day.reason
        })
    
    return JsonResponse({'days_off': data})

@login_required
def get_bookings_counts(request):
    """API для получения количества записей по датам"""
    master = request.user.master
    bookings = Booking.objects.filter(master=master, status='confirmed')
    
    counts = {}
    for booking in bookings:
        date_str = booking.date.strftime('%Y-%m-%d')
        counts[date_str] = counts.get(date_str, 0) + 1
    
    return JsonResponse({'counts': counts})


@login_required
def get_bookings_by_date(request):
    """API для получения записей на конкретную дату"""
    master = request.user.master
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Дата не указана'}, status=400)
    
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    bookings = Booking.objects.filter(
        master=master,
        date=target_date,
        status='confirmed'
    ).order_by('time').select_related('service')
    
    data = []
    for booking in bookings:
        data.append({
            'id': booking.id,
            'time': booking.time.strftime('%H:%M'),
            'client_name': booking.client_name,
            'service_name': booking.service.name,
        })
    
    return JsonResponse({'bookings': data})

@login_required
@require_http_methods(["POST"])
def api_delete_day_off_by_date(request):
    """API удаления выходного дня по дате"""
    master = request.user.master
    data = json.loads(request.body)
    date_str = data.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Дата не указана'}, status=400)
    
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    DayOff.objects.filter(master=master, date=target_date).delete()
    
    return JsonResponse({'success': True})

@login_required
def add_manual_booking(request):
    """Ручное добавление записи мастером"""
    master = request.user.master
    
    if request.method == 'POST':
        client_name = request.POST.get('client_name')
        client_phone = request.POST.get('client_phone')
        service_id = request.POST.get('service')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        comment = request.POST.get('comment', '')
        force = request.POST.get('force', False)
        
        if not all([client_name, client_phone, service_id, date_str, time_str]):
            messages.error(request, 'Заполните все обязательные поля')
            return redirect('add_manual_booking')
        
        # ОЧИЩАЕМ И ВАЛИДИРУЕМ ТЕЛЕФОН
        import re
        client_phone_cleaned = re.sub(r'\D', '', client_phone)
        
        # Проверяем формат российского номера
        if len(client_phone_cleaned) != 11:
            messages.error(request, 'Номер телефона должен содержать 11 цифр')
            return redirect('add_manual_booking')
        
        if not client_phone_cleaned.startswith('7'):
            messages.error(request, 'Номер должен начинаться с 7')
            return redirect('add_manual_booking')
        
        service = get_object_or_404(Service, id=service_id, master=master)
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        booking_time = datetime.strptime(time_str, '%H:%M').time()
        
        # Проверяем, не занято ли время
        calculator = ScheduleCalculator(master)
        slots = calculator.generate_time_slots(booking_date, service.duration)
        
        is_available = any(slot['start'] == time_str for slot in slots)
        if not is_available and not force:
            messages.error(request, 'Это время уже занято. Отметьте "Записать принудительно", чтобы подтвердить.')
            return redirect('add_manual_booking')
        
        # Шифруем ОЧИЩЕННЫЙ телефон
        from cryptography.fernet import Fernet
        key = master.get_encryption_key()
        if key:
            f = Fernet(key)
            encrypted_phone = f.encrypt(client_phone_cleaned.encode())
        else:
            encrypted_phone = client_phone_cleaned.encode()
        
        booking = Booking.objects.create(
            master=master,
            service=service,
            client_name=client_name,
            encrypted_phone=encrypted_phone,
            client_comment=comment,
            date=booking_date,
            time=booking_time,
            status='confirmed'
        )
        
        messages.success(request, f'Запись для {client_name} добавлена!')
        return redirect('dashboard')
    
    # GET запрос - показываем форму
    services = Service.objects.filter(master=master, is_active=True)
    today = date.today()
    
    return render(request, 'masters/add_manual_booking.html', {
        'services': services,
        'today': today,
        'master': master
    })

@login_required
def get_booking_slots_for_master(request):
    """API для получения слотов при ручном добавлении"""
    master = request.user.master
    service_id = request.GET.get('service_id')
    date_str = request.GET.get('date')
    
    if not service_id or not date_str:
        return JsonResponse({'error': 'Не указаны параметры'}, status=400)
    
    try:
        service = Service.objects.get(id=service_id, master=master)
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (Service.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Неверные параметры'}, status=404)
    
    calculator = ScheduleCalculator(master)
    slots = calculator.generate_time_slots(target_date, service.duration)
    
    return JsonResponse({'slots': slots})



@login_required
@require_http_methods(["POST"])
def api_add_day_off(request):
    """API добавления выходного дня"""
    master = request.user.master
    data = json.loads(request.body)
    
    date_str = data.get('date')
    reason = data.get('reason', '')
    
    if not date_str:
        return JsonResponse({'error': 'Выберите дату'}, status=400)
    
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Проверяем на дубликат
    if DayOff.objects.filter(master=master, date=target_date).exists():
        return JsonResponse({'error': 'Этот день уже отмечен как выходной'}, status=400)
    
    day_off = DayOff.objects.create(
        master=master,
        date=target_date,
        reason=reason
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Выходной день добавлен',
        'day_off': {
            'id': day_off.id,
            'date': day_off.date.strftime('%d.%m.%Y'),
            'date_iso': day_off.date.isoformat(),
            'weekday': day_off.date.strftime('%A'),
            'reason': day_off.reason
        }
    })

@login_required
@require_http_methods(["POST"])
def api_delete_day_off(request, dayoff_id):
    """API удаления выходного дня"""
    day_off = get_object_or_404(DayOff, id=dayoff_id, master=request.user.master)
    day_off.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Выходной день удален'
    })

@login_required
def clients_statistics(request):
    """Статистика клиентов мастера"""
    master = request.user.master
    
    # Получаем все записи мастера
    bookings = Booking.objects.filter(
        master=master,
        status='confirmed'
    ).select_related('service')
    
    from collections import defaultdict
    import re
    from cryptography.fernet import Fernet, InvalidToken
    
    # Получаем ключ мастера
    key = master.get_encryption_key()
    
    # Группируем по клиентам
    clients_data = defaultdict(lambda: {
        'name': '',
        'phone': '',
        'total_visits': 0,
        'services': defaultdict(int),
        'last_visit': None,
        'first_visit': None
    })
    
    for booking in bookings:
        # Расшифровываем телефон
        phone = ''
        if key:
            try:
                f = Fernet(key)
                decrypted = f.decrypt(bytes(booking.encrypted_phone)).decode()
                phone = decrypted
            except (InvalidToken, Exception):
                # Если не получилось расшифровать, пробуем как обычную строку
                try:
                    phone = booking.encrypted_phone.decode('utf-8')
                except:
                    phone = str(booking.encrypted_phone)
        else:
            # Если ключа нет, пробуем как обычную строку
            try:
                phone = booking.encrypted_phone.decode('utf-8')
            except:
                phone = str(booking.encrypted_phone)
        
        # Очищаем телефон от не-цифр и форматируем
        phone_cleaned = re.sub(r'\D', '', phone)
        if len(phone_cleaned) == 11:
            formatted_phone = f"{phone_cleaned[0]} {phone_cleaned[1:4]} {phone_cleaned[4:7]}-{phone_cleaned[7:9]}-{phone_cleaned[9:11]}"
        else:
            formatted_phone = phone
        
        # Ключ для группировки (имя + телефон)
        # client_key = f"{booking.client_name}_{phone_cleaned}"
        client_key = phone_cleaned
        
        clients_data[client_key]['name'] = booking.client_name
        clients_data[client_key]['phone'] = formatted_phone
        clients_data[client_key]['total_visits'] += 1
        clients_data[client_key]['services'][booking.service.name] += 1
        
        # Обновляем даты
        if clients_data[client_key]['first_visit'] is None or booking.date < clients_data[client_key]['first_visit']:
            clients_data[client_key]['first_visit'] = booking.date
        if clients_data[client_key]['last_visit'] is None or booking.date > clients_data[client_key]['last_visit']:
            clients_data[client_key]['last_visit'] = booking.date
    
    # Преобразуем в список для шаблона
    clients_list = []
    for client_key, data in clients_data.items():
        # Находим самую популярную услугу
        most_popular_service = max(data['services'].items(), key=lambda x: x[1]) if data['services'] else ('Нет', 0)
        
        clients_list.append({
            'name': data['name'],
            'phone': data['phone'],
            'total_visits': data['total_visits'],
            'most_popular_service': most_popular_service[0],
            'most_popular_service_count': most_popular_service[1],
            'first_visit': data['first_visit'],
            'last_visit': data['last_visit'],
            'services': dict(data['services'])
        })
    
    # Сортируем по количеству визитов
    clients_list.sort(key=lambda x: x['total_visits'], reverse=True)
    
    # Общая статистика
    total_clients = len(clients_list)
    total_bookings = bookings.count()
    avg_visits_per_client = round(total_bookings / total_clients, 1) if total_clients > 0 else 0
    
    context = {
        'clients': clients_list,
        'total_clients': total_clients,
        'total_bookings': total_bookings,
        'avg_visits_per_client': avg_visits_per_client,
        'master': master
    }
    
    return render(request, 'masters/clients_statistics.html', context)


@login_required
def get_clients_statistics_api(request):
    """API для получения статистики клиентов с пагинацией"""
    master = request.user.master
    
    bookings = Booking.objects.filter(
        master=master,
        status='confirmed'
    ).select_related('service')
    
    from collections import defaultdict
    import re
    from cryptography.fernet import Fernet, InvalidToken
    
    key = master.get_encryption_key()
    
    clients_data = defaultdict(lambda: {
        'names': set(),
        'phone': '',
        'total_visits': 0,
        'services': defaultdict(int),
        'last_visit': None,
        'first_visit': None
    })
    
    for booking in bookings:
        # Расшифровка телефона
        phone = ''
        if key:
            try:
                f = Fernet(key)
                decrypted = f.decrypt(bytes(booking.encrypted_phone)).decode()
                phone = decrypted
            except (InvalidToken, Exception):
                try:
                    phone = booking.encrypted_phone.decode('utf-8')
                except:
                    phone = str(booking.encrypted_phone)
        else:
            try:
                phone = booking.encrypted_phone.decode('utf-8')
            except:
                phone = str(booking.encrypted_phone)
        
        phone_cleaned = re.sub(r'\D', '', phone)
        if len(phone_cleaned) == 11:
            formatted_phone = f"{phone_cleaned[0]} {phone_cleaned[1:4]} {phone_cleaned[4:7]}-{phone_cleaned[7:9]}-{phone_cleaned[9:11]}"
        else:
            formatted_phone = phone
        
        client_key = phone_cleaned
        
        clients_data[client_key]['names'].add(booking.client_name)
        clients_data[client_key]['phone'] = formatted_phone
        clients_data[client_key]['total_visits'] += 1
        clients_data[client_key]['services'][booking.service.name] += 1
        
        if clients_data[client_key]['first_visit'] is None or booking.date < clients_data[client_key]['first_visit']:
            clients_data[client_key]['first_visit'] = booking.date
        if clients_data[client_key]['last_visit'] is None or booking.date > clients_data[client_key]['last_visit']:
            clients_data[client_key]['last_visit'] = booking.date
    
    clients_list = []
    for client_key, data in clients_data.items():
        most_popular_service = max(data['services'].items(), key=lambda x: x[1]) if data['services'] else ('Нет', 0)
        
        names_list = list(data['names'])
        if len(names_list) == 1:
            client_name = names_list[0]
        else:
            client_name = f"{names_list[0]} (+{len(names_list)-1})"
        
        clients_list.append({
            'name': client_name,
            'phone': data['phone'],
            'total_visits': data['total_visits'],
            'most_popular_service': most_popular_service[0],
            'most_popular_service_count': most_popular_service[1],
            'first_visit': data['first_visit'].strftime('%d.%m.%Y') if data['first_visit'] else None,
            'last_visit': data['last_visit'].strftime('%d.%m.%Y') if data['last_visit'] else None,
            'services': dict(data['services'])
        })
    
    clients_list.sort(key=lambda x: x['total_visits'], reverse=True)
    
    # Пагинация
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    offset = (page - 1) * limit
    
    total = len(clients_list)
    has_more = offset + limit < total
    clients_page = clients_list[offset:offset + limit]
    
    return JsonResponse({
        'clients': clients_page,
        'total': total,
        'page': page,
        'has_more': has_more
    })



@login_required
def get_decrypted_phone(request, booking_id):
    """API для расшифровки номера телефона"""
    booking = get_object_or_404(Booking, id=booking_id, master=request.user.master)
    
    from cryptography.fernet import Fernet, InvalidToken
    import re
    
    key = request.user.master.get_encryption_key()
    
    if not key:
        return JsonResponse({'error': 'Ключ шифрования не найден'}, status=400)
    
    try:
        f = Fernet(key)
        decrypted = f.decrypt(bytes(booking.encrypted_phone)).decode()
    except InvalidToken:
        # Если не получилось расшифровать, пробуем как обычную строку
        try:
            decrypted = booking.encrypted_phone.decode('utf-8')
        except:
            return JsonResponse({'error': 'Ошибка расшифровки'}, status=400)
    
    # Форматируем для красивого отображения
    phone_cleaned = re.sub(r'\D', '', decrypted)
    if len(phone_cleaned) == 11:
        formatted_phone = f"{phone_cleaned[0]} {phone_cleaned[1:4]} {phone_cleaned[4:7]}-{phone_cleaned[7:9]}-{phone_cleaned[9:11]}"
    else:
        formatted_phone = decrypted
    
    return JsonResponse({'phone': formatted_phone})


from django.contrib.auth import authenticate, login
from .models import PhoneVerification
import random

@csrf_exempt
def mobile_login(request):
    """API вход по телефону и паролю"""
    data = json.loads(request.body)
    phone = data.get('phone')
    password = data.get('password')
    
    user = authenticate(request, username=phone, password=password)
    if user:
        login(request, user)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Неверные данные'}, status=400)

@csrf_exempt
def mobile_register(request):
    """API регистрация (шаг 1)"""
    data = json.loads(request.body)
    phone = data.get('phone')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    password = data.get('password')
    
    if CustomUser.objects.filter(phone=phone).exists():
        return JsonResponse({'error': 'Пользователь уже существует'}, status=400)
    
    verification_code = str(random.randint(100000, 999999))
    PhoneVerification.objects.create(phone=phone, code=verification_code)
    
    request.session['reg_phone'] = phone
    request.session['reg_first_name'] = first_name
    request.session['reg_last_name'] = last_name
    request.session['reg_password'] = password
    request.session['test_code'] = verification_code
    
    return JsonResponse({'success': True, 'test_code': verification_code})

@csrf_exempt
def mobile_verify(request):
    """API подтверждение кода (шаг 2)"""
    data = json.loads(request.body)
    code = data.get('code')
    phone = request.session.get('reg_phone')
    
    verification = PhoneVerification.objects.filter(phone=phone, code=code, is_used=False).first()
    test_code = request.session.get('test_code')
    
    if verification or (test_code and code == test_code):
        if verification:
            verification.is_used = True
            verification.save()
        
        user = CustomUser.objects.create_user(
            phone=phone,
            password=request.session.get('reg_password'),
            first_name=request.session.get('reg_first_name', ''),
            last_name=request.session.get('reg_last_name', '')
        )
        Master.objects.create(
            user=user,
            phone=phone,
            first_name=request.session.get('reg_first_name', ''),
            last_name=request.session.get('reg_last_name', '')
        )
        login(request, user)
        
        # Очищаем сессию
        for key in ['reg_phone', 'reg_first_name', 'reg_last_name', 'reg_password', 'test_code']:
            request.session.pop(key, None)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Неверный код'}, status=400)

@csrf_exempt
def mobile_resend_code(request):
    """API повторная отправка кода"""
    data = json.loads(request.body)
    phone = data.get('phone') or request.session.get('reg_phone')
    
    verification_code = str(random.randint(100000, 999999))
    PhoneVerification.objects.create(phone=phone, code=verification_code)
    request.session['test_code'] = verification_code
    
    return JsonResponse({'success': True, 'test_code': verification_code})


# Выход
def logout_view(request):
    auth_logout(request)
    # messages.success(request, 'Вы вышли из системы')
    return redirect('home')

from django.http import JsonResponse
from .utils.schedule_utils import ScheduleCalculator
import json

# ... (существующий код) ...

# def master_public_page(request, slug):
#     """Публичная страница мастера для записи"""
#     master = get_object_or_404(Master, slug=slug)
#     services = Service.objects.filter(master=master, is_active=True)
    
#     return render(request, 'masters/public/master_page.html', {
#         'master': master,
#         'services': services
#     })


def get_available_dates(request, login):
    """API для получения доступных дат"""
    # master = get_object_or_404(Master, slug=slug)
    master = get_object_or_404(Master, login=login)
    service_id = request.GET.get('service_id')
    
    if not service_id:
        return JsonResponse({'error': 'Выберите услугу'}, status=400)
    
    try:
        service = Service.objects.get(id=service_id, master=master)
    except Service.DoesNotExist:
        return JsonResponse({'error': 'Услуга не найдена'}, status=404)
    
    calculator = ScheduleCalculator(master)
    available_dates = calculator.get_available_dates(
        days_ahead=60,
        min_service_duration=service.duration
    )
    
    dates_list = [{
        'date': d.strftime('%Y-%m-%d'),
        'display': f"{d.day} {get_month_ru(d)} {d.year}",
        'day_of_week': get_weekday_ru(d)
    } for d in available_dates]
    
    return JsonResponse({'dates': dates_list})



def get_available_slots(request, login):
    """API для получения свободных слотов на выбранную дату"""
    # master = get_object_or_404(Master, slug=slug)
    master = get_object_or_404(Master, login=login)
    service_id = request.GET.get('service_id')
    date_str = request.GET.get('date')
    
    if not service_id or not date_str:
        return JsonResponse({'error': 'Не указаны параметры'}, status=400)
    
    try:
        service = Service.objects.get(id=service_id, master=master)
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (Service.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Неверные параметры'}, status=404)
    
    # Рассчитываем свободные слоты
    calculator = ScheduleCalculator(master)
    slots = calculator.generate_time_slots(target_date, service.duration)
    
    return JsonResponse({'slots': slots})

def create_booking(request, login):
    """Создание новой записи (без перезагрузки)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    
    # master = get_object_or_404(Master, slug=slug)
    master = get_object_or_404(Master, login=login)
    
    try:
        data = json.loads(request.body)
        service_id = data.get('service_id')
        client_name = data.get('client_name')
        client_phone = data.get('client_phone')
        date_str = data.get('date')
        time_str = data.get('time')
        comment = data.get('comment', '')
        force = data.get('force', False)
        
        # Проверяем обязательные поля
        if not all([service_id, client_name, client_phone, date_str, time_str]):
            return JsonResponse({'error': 'Заполните все поля'}, status=400)
        
        # ОЧИЩАЕМ И ВАЛИДИРУЕМ ТЕЛЕФОН
        import re
        client_phone_cleaned = re.sub(r'\D', '', client_phone)
        
        # Проверяем формат российского номера
        if len(client_phone_cleaned) != 11:
            return JsonResponse({'error': 'Номер телефона должен содержать 11 цифр'}, status=400)
        
        if not client_phone_cleaned.startswith('7'):
            return JsonResponse({'error': 'Номер должен начинаться с 7'}, status=400)
        
        service = Service.objects.get(id=service_id, master=master)
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        booking_time = datetime.strptime(time_str, '%H:%M').time()
        
        # Проверяем, свободно ли это время
        calculator = ScheduleCalculator(master)
        slots = calculator.generate_time_slots(booking_date, service.duration)
        
        is_available = any(slot['start'] == time_str for slot in slots)
        if not is_available and not force:
            return JsonResponse({'error': 'Это время уже занято'}, status=400)
        
        # Шифруем ОЧИЩЕННЫЙ телефон
        from cryptography.fernet import Fernet
        key = master.get_encryption_key()
        if key:
            f = Fernet(key)
            encrypted_phone = f.encrypt(client_phone_cleaned.encode())
        else:
            # Временное решение, если ключа нет
            encrypted_phone = client_phone_cleaned.encode()
        
        # Создаем запись
        booking = Booking.objects.create(
            master=master,
            service=service,
            client_name=client_name,
            encrypted_phone=encrypted_phone,
            client_comment=comment,
            date=booking_date,
            time=booking_time,
            status='confirmed' if not force else 'confirmed'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Запись создана!',
            'booking': {
                'id': booking.id,
                'date': booking.date.strftime('%d.%m.%Y'),
                'time': booking.time.strftime('%H:%M'),
                'service': service.name
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def master_by_id(request, master_id):
    """Публичная страница мастера по ID"""
    master = get_object_or_404(Master, id=master_id)
    services = Service.objects.filter(master=master, is_active=True)
    
    return render(request, 'masters/public/master_page.html', {
        'master': master,
        'services': services
    })

def master_by_login(request, login):
    """Публичная страница мастера по логину"""
    master = get_object_or_404(Master, login=login)
    services = Service.objects.filter(master=master, is_active=True)
    
    return render(request, 'masters/public/master_page.html', {
        'master': master,
        'services': services
    })


# В views.py добавим функцию форматирования
def format_phone(phone):
    """Форматирует 79991234567 -> 7 999 123-45-67"""
    if not phone or len(phone) != 11:
        return phone
    return f"{phone[0]} {phone[1:4]} {phone[4:7]}-{phone[7:9]}-{phone[9:11]}"



@login_required
def get_day_status(request):
    """API для получения статуса конкретного дня"""
    master = request.user.master
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Дата не указана'}, status=400)
    
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    day_of_week = target_date.weekday()
    
    extra_day = ExtraWorkingDay.objects.filter(master=master, date=target_date).first()
    is_day_off = DayOff.objects.filter(master=master, date=target_date).exists()
    schedule = Schedule.objects.filter(master=master, day_of_week=day_of_week).first()
    
    # Формируем список перерывов
    breaks = []
    if extra_day:
        breaks = [{
            'start': b.start_time.strftime('%H:%M'),
            'end': b.end_time.strftime('%H:%M')
        } for b in extra_day.breaks.all()]
    
    return JsonResponse({
        'is_extra': extra_day is not None,
        'is_day_off': is_day_off,
        'has_schedule': schedule is not None,
        'schedule_start': schedule.start_time.strftime('%H:%M') if schedule else None,
        'schedule_end': schedule.end_time.strftime('%H:%M') if schedule else None,
        'extra_start': extra_day.start_time.strftime('%H:%M') if extra_day else None,
        'extra_end': extra_day.end_time.strftime('%H:%M') if extra_day else None,
        'breaks': breaks,
        'date': date_str
    })


@login_required
@require_http_methods(["POST"])
def api_delete_extra_day_by_date(request):
    """API удаления дополнительного рабочего дня по дате"""
    master = request.user.master
    data = json.loads(request.body)
    date_str = data.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Дата не указана'}, status=400)
    
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    ExtraWorkingDay.objects.filter(master=master, date=target_date).delete()
    
    return JsonResponse({'success': True})















    # Регистрация шаг 1
# def register_step1(request):
#     """Шаг 1 регистрации: ввод телефона и пароля"""
#     if request.method == 'POST':
#         form = PhoneRegistrationForm(request.POST)
#         if form.is_valid():
#             # Очищаем и проверяем телефон
#             import re
#             phone_cleaned = re.sub(r'\D', '', form.cleaned_data['phone'])
            
#             if len(phone_cleaned) != 11 or not phone_cleaned.startswith('7'):
#                 messages.error(request, 'Неверный формат телефона. Нужен номер 7XXXXXXXXXX (11 цифр)')
#                 return render(request, 'masters/register_step1.html', {'form': form})
            
#             request.session['registration_data'] = {
#                 'phone': phone_cleaned,  # сохраняем очищенный
#                 'first_name': form.cleaned_data.get('first_name', ''),
#                 'last_name': form.cleaned_data.get('last_name', ''),
#                 'password': form.cleaned_data['password'],
#             }
            
#             verification_code = str(random.randint(100000, 999999))
            
#             PhoneVerification.objects.create(
#                 phone=phone_cleaned,
#                 code=verification_code
#             )
            
#             request.session['test_code'] = verification_code
            
#             return redirect('verify_phone')
#         else:
#             for error in form.non_field_errors():
#                 messages.error(request, error)
#             for field, errors in form.errors.items():
#                 if field != '__all__':
#                     for error in errors:
#                         messages.error(request, f'{error}')
#     else:
#         form = PhoneRegistrationForm()
    
#     return render(request, 'masters/register_step1.html', {'form': form})

# Регистрация шаг 2 - подтверждение кода
# def verify_phone(request):
#     registration_data = request.session.get('registration_data')
#     if not registration_data:
#         return redirect('register')
    
#     test_code = request.session.get('test_code')
    
#     if request.method == 'POST':
#         form = PhoneVerificationForm(request.POST)
#         if form.is_valid():
#             code = form.cleaned_data['code']
            
#             verification = PhoneVerification.objects.filter(
#                 phone=registration_data['phone'],
#                 code=code,
#                 is_used=False
#             ).first()
            
#             if verification or (test_code and code == test_code):
#                 if verification:
#                     verification.is_used = True
#                     verification.save()
                
#                 user = CustomUser.objects.create_user(
#                     phone=registration_data['phone'],
#                     password=registration_data['password'],
#                     first_name=registration_data.get('first_name', ''),
#                     last_name=registration_data.get('last_name', '')
#                 )
                
#                 Master.objects.create(
#                     user=user,
#                     phone=registration_data['phone'],
#                     first_name=registration_data.get('first_name', ''),
#                     last_name=registration_data.get('last_name', '')
#                 )
                
#                 login(request, user)
                
#                 del request.session['registration_data']
#                 if 'test_code' in request.session:
#                     del request.session['test_code']
                
#                 messages.success(request, 'Регистрация прошла успешно!')
#                 return redirect('dashboard')
#             else:
#                 messages.error(request, 'Неверный код подтверждения')
#         else:
#             messages.error(request, 'Введите код подтверждения')
#     else:
#         form = PhoneVerificationForm()
    
#     return render(request, 'masters/verify_phone.html', {
#         'form': form,
#         'phone': registration_data['phone'],
#         'test_code': test_code
#     })

# Повторная отправка кода
# def resend_code(request):
#     registration_data = request.session.get('registration_data')
#     if not registration_data:
#         return redirect('register')
    
#     verification_code = str(random.randint(100000, 999999))
    
#     PhoneVerification.objects.create(
#         phone=registration_data['phone'],
#         code=verification_code
#     )
    
#     request.session['test_code'] = verification_code
    
#     messages.success(request, 'Новый код отправлен!')
#     return redirect('verify_phone')

# Кастомный вход
# class CustomLoginView(LoginView):
#     template_name = 'masters/login.html'
#     redirect_authenticated_user = True
    
#     def form_invalid(self, form):
#         messages.error(self.request, 'Неверный телефон или пароль')
#         return super().form_invalid(form)
    
#     def get_success_url(self):
#         return reverse_lazy('dashboard')



# @login_required
# def add_service(request):
#     if request.method == 'POST':
#         master = request.user.master
#         name = request.POST.get('name')
#         description = request.POST.get('description', '')
#         duration = request.POST.get('duration')
#         price = request.POST.get('price')
        
#         if name and duration and price:
#             Service.objects.create(
#                 master=master,
#                 name=name,
#                 description=description,
#                 duration=duration,
#                 price=price
#             )
#             messages.success(request, 'Услуга добавлена!')
#         else:
#             messages.error(request, 'Заполните все обязательные поля')
        
#         return redirect('services')
    
#     return render(request, 'masters/add_service.html')

# @login_required
# def edit_service(request, service_id):
#     service = get_object_or_404(Service, id=service_id, master=request.user.master)
    
#     if request.method == 'POST':
#         service.name = request.POST.get('name')
#         service.description = request.POST.get('description', '')
#         service.duration = request.POST.get('duration')
#         service.price = request.POST.get('price')
#         service.save()
#         messages.success(request, 'Услуга обновлена!')
#         return redirect('services')
    
#     return render(request, 'masters/edit_service.html', {'service': service})

# @login_required
# def delete_service(request, service_id):
#     service = get_object_or_404(Service, id=service_id, master=request.user.master)
#     service.delete()
#     messages.success(request, 'Услуга удалена!')
#     return redirect('services')