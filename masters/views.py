from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .models import Master, Service, Booking, Schedule, DayOff
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, time, timedelta

# Create your views here.

def home(request):
    """Главная страница"""
    return render(request, 'masters/index.html')

class CustomLoginView(LoginView):
    """Кастомная страница входа"""
    template_name = 'masters/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')

def register(request):
    """Регистрация нового мастера"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Автоматически логиним пользователя
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Исправьте ошибки в форме')
    else:
        form = UserCreationForm()
    
    return render(request, 'masters/register.html', {'form': form})

@login_required
def dashboard(request):
    """Личный кабинет мастера"""
    try:
        master = request.user.master
    except Master.DoesNotExist:
        # Если по какой-то причине нет мастера, создаем
        master = Master.objects.create(user=request.user)
    
    # Получаем статистику
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
def profile(request):
    """Редактирование профиля"""
    try:
        master = request.user.master
    except Master.DoesNotExist:
        master = Master.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Обновляем данные
        master.phone = request.POST.get('phone', '')
        master.first_name = request.POST.get('first_name', '')
        master.last_name = request.POST.get('last_name', '')
        master.bio = request.POST.get('bio', '')
        master.save()
        
        # Обновляем имя пользователя в User
        user = request.user
        user.first_name = master.first_name
        user.last_name = master.last_name
        user.save()
        
        messages.success(request, 'Профиль обновлен!')
        return redirect('profile')
    
    return render(request, 'masters/profile.html', {'master': master})

@login_required
def services(request):
    """Список услуг мастера"""
    master = request.user.master
    services_list = Service.objects.filter(master=master)
    return render(request, 'masters/services.html', {'services': services_list})

@login_required
def add_service(request):
    """Добавление услуги"""
    if request.method == 'POST':
        master = request.user.master
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        duration = request.POST.get('duration')
        price = request.POST.get('price')
        
        if name and duration and price:
            Service.objects.create(
                master=master,
                name=name,
                description=description,
                duration=duration,
                price=price
            )
            messages.success(request, 'Услуга добавлена!')
        else:
            messages.error(request, 'Заполните все обязательные поля')
        
        return redirect('services')
    
    return render(request, 'masters/add_service.html')

@login_required
def edit_service(request, service_id):
    """Редактирование услуги"""
    service = get_object_or_404(Service, id=service_id, master=request.user.master)
    
    if request.method == 'POST':
        service.name = request.POST.get('name')
        service.description = request.POST.get('description', '')
        service.duration = request.POST.get('duration')
        service.price = request.POST.get('price')
        service.save()
        messages.success(request, 'Услуга обновлена!')
        return redirect('services')
    
    return render(request, 'masters/edit_service.html', {'service': service})

@login_required
def delete_service(request, service_id):
    """Удаление услуги"""
    service = get_object_or_404(Service, id=service_id, master=request.user.master)
    service.delete()
    messages.success(request, 'Услуга удалена!')
    return redirect('services')

@login_required
def schedule(request):
    """Настройка регулярного расписания"""
    master = request.user.master
    schedules = Schedule.objects.filter(master=master).order_by('day_of_week')
    
    # Словарь для названий дней недели
    days = dict(Schedule.DAYS_OF_WEEK)
    
    return render(request, 'masters/schedule.html', {
        'schedules': schedules,
        'days': days
    })

@login_required
def add_schedule(request):
    """Добавление рабочего дня в расписание"""
    if request.method == 'POST':
        master = request.user.master
        day_of_week = request.POST.get('day_of_week')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        # Проверяем, не существует ли уже запись для этого дня
        existing = Schedule.objects.filter(master=master, day_of_week=day_of_week).first()
        if existing:
            messages.error(request, 'Расписание для этого дня уже существует')
            return redirect('schedule')
        
        if day_of_week and start_time and end_time:
            # Преобразуем строки времени в объекты time
            start = datetime.strptime(start_time, '%H:%M').time()
            end = datetime.strptime(end_time, '%H:%M').time()
            
            Schedule.objects.create(
                master=master,
                day_of_week=day_of_week,
                start_time=start,
                end_time=end
            )
            messages.success(request, 'Расписание добавлено')
        else:
            messages.error(request, 'Заполните все поля')
        
        return redirect('schedule')
    
    return render(request, 'masters/add_schedule.html')

@login_required
def delete_schedule(request, schedule_id):
    """Удаление расписания"""
    schedule = get_object_or_404(Schedule, id=schedule_id, master=request.user.master)
    schedule.delete()
    messages.success(request, 'Расписание удалено')
    return redirect('schedule')

@login_required
def days_off(request):
    """Список выходных дней"""
    master = request.user.master
    days_off_list = DayOff.objects.filter(master=master, date__gte=timezone.now().date()).order_by('date')
    past_days_off = DayOff.objects.filter(master=master, date__lt=timezone.now().date()).order_by('-date')[:5]
    
    return render(request, 'masters/days_off.html', {
        'days_off': days_off_list,
        'past_days_off': past_days_off
    })

@login_required
def add_day_off(request):
    """Добавление выходного дня"""
    if request.method == 'POST':
        master = request.user.master
        date_str = request.POST.get('date')
        reason = request.POST.get('reason', '')
        
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Проверяем, не выходной ли уже этот день
            existing = DayOff.objects.filter(master=master, date=date_obj).first()
            if existing:
                messages.error(request, 'Этот день уже отмечен как выходной')
                return redirect('days_off')
            
            DayOff.objects.create(
                master=master,
                date=date_obj,
                reason=reason
            )
            messages.success(request, 'Выходной день добавлен')
        else:
            messages.error(request, 'Выберите дату')
        
        return redirect('days_off')
    
    return render(request, 'masters/add_day_off.html')

@login_required
def delete_day_off(request, dayoff_id):
    """Удаление выходного дня"""
    day_off = get_object_or_404(DayOff, id=dayoff_id, master=request.user.master)
    day_off.delete()
    messages.success(request, 'Выходной день удален')
    return redirect('days_off')



from django.http import JsonResponse
from .utils.schedule_utils import ScheduleCalculator
import json

# ... (существующий код) ...

def master_public_page(request, slug):
    """Публичная страница мастера для записи"""
    master = get_object_or_404(Master, slug=slug)
    services = Service.objects.filter(master=master, is_active=True)
    
    return render(request, 'masters/public/master_page.html', {
        'master': master,
        'services': services
    })

def get_available_dates(request, slug):
    """API для получения доступных дат (без перезагрузки страницы)"""
    master = get_object_or_404(Master, slug=slug)
    service_id = request.GET.get('service_id')
    
    if not service_id:
        return JsonResponse({'error': 'Выберите услугу'}, status=400)
    
    try:
        service = Service.objects.get(id=service_id, master=master)
    except Service.DoesNotExist:
        return JsonResponse({'error': 'Услуга не найдена'}, status=404)
    
    # Рассчитываем доступные даты
    calculator = ScheduleCalculator(master)
    available_dates = calculator.get_available_dates(
        days_ahead=30, 
        min_service_duration=service.duration
    )
    
    # Форматируем даты для JSON
    dates_list = [{
        'date': d.strftime('%Y-%m-%d'),
        'display': d.strftime('%d %B %Y'),  # например: "15 марта 2026"
        'day_of_week': d.strftime('%A')  # день недели
    } for d in available_dates]
    
    return JsonResponse({'dates': dates_list})

def get_available_slots(request, slug):
    """API для получения свободных слотов на выбранную дату"""
    master = get_object_or_404(Master, slug=slug)
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

def create_booking(request, slug):
    """Создание новой записи (без перезагрузки)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    
    master = get_object_or_404(Master, slug=slug)
    
    try:
        data = json.loads(request.body)
        service_id = data.get('service_id')
        client_name = data.get('client_name')
        client_phone = data.get('client_phone')
        date_str = data.get('date')
        time_str = data.get('time')
        comment = data.get('comment', '')
        
        # Проверяем обязательные поля
        if not all([service_id, client_name, client_phone, date_str, time_str]):
            return JsonResponse({'error': 'Заполните все поля'}, status=400)
        
        service = Service.objects.get(id=service_id, master=master)
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        booking_time = datetime.strptime(time_str, '%H:%M').time()
        
        # Проверяем, свободно ли это время
        calculator = ScheduleCalculator(master)
        slots = calculator.generate_time_slots(booking_date, service.duration)
        
        is_available = any(slot['start'] == time_str for slot in slots)
        if not is_available:
            return JsonResponse({'error': 'Это время уже занято'}, status=400)
        
        # Шифруем телефон (пока просто заглушка)
        # TODO: добавить реальное шифрование
        
        # Создаем запись
        booking = Booking.objects.create(
            master=master,
            service=service,
            client_name=client_name,
            encrypted_phone=client_phone.encode(),  # временно, потом заменим на шифрование
            client_comment=comment,
            date=booking_date,
            time=booking_time
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