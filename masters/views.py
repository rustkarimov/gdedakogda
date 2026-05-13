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
from .models import Master, Service, Booking, Schedule, DayOff, PhoneVerification, CustomUser, Break
from .forms import PhoneRegistrationForm, PhoneVerificationForm
from .utils.schedule_utils import ScheduleCalculator
from datetime import datetime, timedelta, date
import random
import json

# В начале файла добавь импорты
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

# Регистрация шаг 1
def register_step1(request):
    if request.method == 'POST':
        form = PhoneRegistrationForm(request.POST)
        if form.is_valid():
            request.session['registration_data'] = {
                'phone': form.cleaned_data['phone'],
                'first_name': form.cleaned_data.get('first_name', ''),
                'last_name': form.cleaned_data.get('last_name', ''),
                'password': form.cleaned_data['password'],
            }
            
            verification_code = str(random.randint(100000, 999999))
            
            PhoneVerification.objects.create(
                phone=form.cleaned_data['phone'],
                code=verification_code
            )
            
            request.session['test_code'] = verification_code
            
            return redirect('verify_phone')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for field, errors in form.errors.items():
                if field != '__all__':
                    for error in errors:
                        messages.error(request, f'{error}')
    else:
        form = PhoneRegistrationForm()
    
    return render(request, 'masters/register_step1.html', {'form': form})

# Регистрация шаг 2 - подтверждение кода
def verify_phone(request):
    registration_data = request.session.get('registration_data')
    if not registration_data:
        return redirect('register')
    
    test_code = request.session.get('test_code')
    
    if request.method == 'POST':
        form = PhoneVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            verification = PhoneVerification.objects.filter(
                phone=registration_data['phone'],
                code=code,
                is_used=False
            ).first()
            
            if verification or (test_code and code == test_code):
                if verification:
                    verification.is_used = True
                    verification.save()
                
                user = CustomUser.objects.create_user(
                    phone=registration_data['phone'],
                    password=registration_data['password'],
                    first_name=registration_data.get('first_name', ''),
                    last_name=registration_data.get('last_name', '')
                )
                
                Master.objects.create(
                    user=user,
                    phone=registration_data['phone'],
                    first_name=registration_data.get('first_name', ''),
                    last_name=registration_data.get('last_name', '')
                )
                
                login(request, user)
                
                del request.session['registration_data']
                if 'test_code' in request.session:
                    del request.session['test_code']
                
                messages.success(request, 'Регистрация прошла успешно!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Неверный код подтверждения')
        else:
            messages.error(request, 'Введите код подтверждения')
    else:
        form = PhoneVerificationForm()
    
    return render(request, 'masters/verify_phone.html', {
        'form': form,
        'phone': registration_data['phone'],
        'test_code': test_code
    })

# Повторная отправка кода
def resend_code(request):
    registration_data = request.session.get('registration_data')
    if not registration_data:
        return redirect('register')
    
    verification_code = str(random.randint(100000, 999999))
    
    PhoneVerification.objects.create(
        phone=registration_data['phone'],
        code=verification_code
    )
    
    request.session['test_code'] = verification_code
    
    messages.success(request, 'Новый код отправлен!')
    return redirect('verify_phone')

# Кастомный вход
class CustomLoginView(LoginView):
    template_name = 'masters/login.html'
    redirect_authenticated_user = True
    
    def form_invalid(self, form):
        messages.error(self.request, 'Неверный телефон или пароль')
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('dashboard')

# Выход
def logout_view(request):
    auth_logout(request)
    messages.success(request, 'Вы вышли из системы')
    return redirect('home')

# Главная страница
def home(request):
    return render(request, 'masters/index.html')

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
    """API для получения расписания мастера для календаря"""
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
    
    # Получаем выходные дни (только будущие)
    days_off = DayOff.objects.filter(
        master=master,
        date__gte=date.today()
    ).values_list('date', flat=True)
    
    days_off_list = [d.strftime('%Y-%m-%d') for d in days_off]
    
    return JsonResponse({
        'schedules': schedules_data,
        'days_off': days_off_list
    })

# Профиль
@login_required
def profile(request):
    try:
        master = request.user.master
    except Master.DoesNotExist:
        master = Master.objects.create(user=request.user)
    
    if request.method == 'POST':
        master.phone = request.POST.get('phone', '')
        master.first_name = request.POST.get('first_name', '')
        master.last_name = request.POST.get('last_name', '')
        master.bio = request.POST.get('bio', '')
        master.save()
        
        messages.success(request, 'Профиль обновлен!')
        return redirect('profile')
    
    return render(request, 'masters/profile.html', {'master': master})

# Услуги
@login_required
def services(request):
    master = request.user.master
    services_list = Service.objects.filter(master=master)
    return render(request, 'masters/services.html', {'services': services_list})

@login_required
def add_service(request):
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
    service = get_object_or_404(Service, id=service_id, master=request.user.master)
    service.delete()
    messages.success(request, 'Услуга удалена!')
    return redirect('services')


@login_required
def schedule(request):
    """Настройка регулярного расписания (AJAX версия)"""
    master = request.user.master
    schedules = Schedule.objects.filter(master=master).order_by('day_of_week')
    
    return render(request, 'masters/schedule.html', {
        'schedules': schedules,
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
        
        if not all([client_name, client_phone, service_id, date_str, time_str]):
            messages.error(request, 'Заполните все обязательные поля')
            return redirect('add_manual_booking')
        
        service = get_object_or_404(Service, id=service_id, master=master)
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        booking_time = datetime.strptime(time_str, '%H:%M').time()
        
        # Проверяем, не занято ли время
        calculator = ScheduleCalculator(master)
        slots = calculator.generate_time_slots(booking_date, service.duration)
        
        is_available = any(slot['start'] == time_str for slot in slots)
        if not is_available and not request.POST.get('force', False):
            messages.error(request, 'Это время уже занято. Нажмите "Записать принудительно", чтобы подтвердить.')
            return redirect('add_manual_booking')
        
        # Шифруем телефон (пока временно)
        encrypted_phone = client_phone.encode()
        
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

# Выходные дни
# @login_required
# def days_off(request):
#     master = request.user.master
#     days_off_list = DayOff.objects.filter(master=master, date__gte=datetime.now().date()).order_by('date')
#     past_days_off = DayOff.objects.filter(master=master, date__lt=datetime.now().date()).order_by('-date')[:5]
    
#     return render(request, 'masters/days_off.html', {
#         'days_off': days_off_list,
#         'past_days_off': past_days_off
#     })

# @login_required
# def add_day_off(request):
#     if request.method == 'POST':
#         master = request.user.master
#         date_str = request.POST.get('date')
#         reason = request.POST.get('reason', '')
        
#         if date_str:
#             date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
#             existing = DayOff.objects.filter(master=master, date=date_obj).first()
#             if existing:
#                 messages.error(request, 'Этот день уже отмечен как выходной')
#                 return redirect('days_off')
            
#             DayOff.objects.create(
#                 master=master,
#                 date=date_obj,
#                 reason=reason
#             )
#             messages.success(request, 'Выходной день добавлен')
#         else:
#             messages.error(request, 'Выберите дату')
        
#         return redirect('days_off')
    
#     return render(request, 'masters/add_day_off.html')

# @login_required
# def delete_day_off(request, dayoff_id):
#     day_off = get_object_or_404(DayOff, id=dayoff_id, master=request.user.master)
#     day_off.delete()
#     messages.success(request, 'Выходной день удален')
#     return redirect('days_off')



@login_required
def days_off(request):
    """Страница выходных дней (AJAX версия)"""
    master = request.user.master
    days_off_list = DayOff.objects.filter(master=master, date__gte=date.today()).order_by('date')
    past_days_off = DayOff.objects.filter(master=master, date__lt=date.today()).order_by('-date')[:5]
    
    return render(request, 'masters/days_off.html', {
        'days_off': days_off_list,
        'past_days_off': past_days_off
    })

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