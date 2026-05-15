from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Аутентификация
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_step1, name='register'),
    path('verify/', views.verify_phone, name='verify_phone'),
    path('resend-code/', views.resend_code, name='resend_code'),

    # Личный кабинет
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),

    path('api/schedule/calendar/', views.get_calendar_schedule, name='api_calendar_schedule'),
    
    # Услуги
    path('services/', views.services, name='services'),
    path('services/add/', views.add_service, name='add_service'),
    path('services/<int:service_id>/edit/', views.edit_service, name='edit_service'),
    path('services/<int:service_id>/delete/', views.delete_service, name='delete_service'),
    
    # Расписание
    path('schedule/', views.schedule, name='schedule'),
    path('schedule/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),

    # API для расписания (AJAX)
    path('api/schedule/add/', views.api_add_schedule, name='api_add_schedule'),
    path('api/schedule/<int:schedule_id>/edit/', views.api_edit_schedule, name='api_edit_schedule'),
    path('api/schedule/<int:schedule_id>/delete/', views.api_delete_schedule, name='api_delete_schedule'),
    
    # Ручное добавление записи
    path('add-booking/', views.add_manual_booking, name='add_manual_booking'),
    path('api/get-slots/', views.get_booking_slots_for_master, name='api_get_slots'),
    
    # Дополнительные рабочие дни
    path('api/extra-days/', views.get_extra_days, name='api_extra_days'),
    path('api/extra-days/add/', views.api_add_extra_day, name='api_add_extra_day'),
    path('api/extra-days/<int:extra_day_id>/delete/', views.api_delete_extra_day, name='api_delete_extra_day'),

    # Выходные дни
    path('days-off/', views.days_off, name='days_off'),
    path('api/days-off/add/', views.api_add_day_off, name='api_add_day_off'),
    path('api/days-off/<int:dayoff_id>/delete/', views.api_delete_day_off, name='api_delete_day_off'),

    # Публичная страница мастера
    path('master/<slug:slug>/', views.master_public_page, name='master_public'),
    
    # API для AJAX-запросов
    path('api/master/<slug:slug>/dates/', views.get_available_dates, name='api_dates'),
    path('api/master/<slug:slug>/slots/', views.get_available_slots, name='api_slots'),
    path('api/master/<slug:slug>/book/', views.create_booking, name='api_book'),
]