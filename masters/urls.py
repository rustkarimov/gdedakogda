from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    
    path('', views.home, name='home'),
    
    # Аутентификация
    path('logout/', views.logout_view, name='logout'),

    # Личный кабинет
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('api/schedule/calendar/', views.get_calendar_schedule, name='api_calendar_schedule'),
    path('api/bookings/', views.get_bookings_api, name='api_bookings'),
    
    # Услуги
    path('services/', views.services, name='services'),
    path('api/services/add/', views.api_add_service, name='api_add_service'),
    path('api/services/<int:service_id>/edit/', views.api_edit_service, name='api_edit_service'),
    path('api/services/<int:service_id>/delete/', views.api_delete_service, name='api_delete_service'),

    # Категории услуг
    path('api/categories/', views.get_categories, name='api_categories'),
    path('api/categories/add/', views.api_add_category, name='api_add_category'),
    path('api/categories/<int:category_id>/edit/', views.api_edit_category, name='api_edit_category'),
    path('api/categories/<int:category_id>/delete/', views.api_delete_category, name='api_delete_category'),
    path('api/services/<int:service_id>/get/', views.api_get_service, name='api_get_service'),

    # API для категорий мастера (публичная страница)
    path('api/master/<str:login>/categories/', views.get_master_categories, name='api_master_categories'),
    
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
    path('api/extra-days/list/', views.get_extra_days_list, name='api_extra_days_list'),
    path('api/extra-days/add/', views.api_add_extra_day, name='api_add_extra_day'),
    path('api/extra-days/<int:extra_day_id>/delete/', views.api_delete_extra_day, name='api_delete_extra_day'),
    path('api/extra-days/delete-by-date/', views.api_delete_extra_day_by_date, name='api_delete_extra_day_by_date'),

    # Статус дня
    path('api/day-status/', views.get_day_status, name='api_day_status'),

    # Выходные дни
    path('api/days-off/list/', views.get_days_off_list, name='api_days_off_list'),
    path('api/days-off/add/', views.api_add_day_off, name='api_add_day_off'),
    path('api/days-off/<int:dayoff_id>/delete/', views.api_delete_day_off, name='api_delete_day_off'),

    #количество записей
    path('api/bookings/counts/', views.get_bookings_counts, name='api_bookings_counts'),
    path('api/bookings/by-date/', views.get_bookings_by_date, name='api_bookings_by_date'),
    path('api/days-off/delete-by-date/', views.api_delete_day_off_by_date, name='api_delete_day_off_by_date'),

    # Статистика клиентов
    path('clients-statistics/', views.clients_statistics, name='clients_statistics'),
    path('api/clients-statistics/', views.get_clients_statistics_api, name='api_clients_statistics'),
    path('api/get-decrypted-phone/<int:booking_id>/', views.get_decrypted_phone, name='api_decrypted_phone'),

    # Публичная страница мастера
    path('id<int:master_id>/', views.master_by_id, name='master_by_id'),
    path('<str:login>/', views.master_by_login, name='master_by_login'),
    
    # API для AJAX-запросов
    path('api/<str:login>/dates/', views.get_available_dates, name='api_dates'),
    path('api/<str:login>/slots/', views.get_available_slots, name='api_slots'),
    path('api/<str:login>/book/', views.create_booking, name='api_book'),

    # Мобильные/модальные API
    path('api/mobile/login/', views.mobile_login, name='mobile_login'),
    path('api/mobile/register/', views.mobile_register, name='mobile_register'),
    path('api/mobile/verify/', views.mobile_verify, name='mobile_verify'),
    path('api/mobile/resend-code/', views.mobile_resend_code, name='mobile_resend_code'),
]