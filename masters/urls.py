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
    
    # Услуги
    path('services/', views.services, name='services'),
    path('services/add/', views.add_service, name='add_service'),
    path('services/<int:service_id>/edit/', views.edit_service, name='edit_service'),
    path('services/<int:service_id>/delete/', views.delete_service, name='delete_service'),
    
    # Расписание
    path('schedule/', views.schedule, name='schedule'),
    path('schedule/add/', views.add_schedule, name='add_schedule'),
    path('schedule/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),
    
    # Выходные дни
    path('days-off/', views.days_off, name='days_off'),
    path('days-off/add/', views.add_day_off, name='add_day_off'),
    path('days-off/<int:dayoff_id>/delete/', views.delete_day_off, name='delete_day_off'),

    # Публичная страница мастера
    path('master/<slug:slug>/', views.master_public_page, name='master_public'),
    
    # API для AJAX-запросов
    path('api/master/<slug:slug>/dates/', views.get_available_dates, name='api_dates'),
    path('api/master/<slug:slug>/slots/', views.get_available_slots, name='api_slots'),
    path('api/master/<slug:slug>/book/', views.create_booking, name='api_book'),
]