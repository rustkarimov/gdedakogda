from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    
    path('', views.home, name='home'),


    path('privacy/', views.privacy_policy, name='privacy'),
    path('terms/', views.terms_of_service, name='terms'),
    path('agree/', views.agree, name='agree'),
    
    # Аутентификация
    path('logout/', views.logout_view, name='logout'),

    # Личный кабинет
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('api/schedule/calendar/', views.get_calendar_schedule, name='api_calendar_schedule'),
    path('api/bookings/', views.get_bookings_api, name='api_bookings'),

    # Детали записи
    path('api/booking/<int:booking_id>/details/', views.get_booking_details, name='api_booking_details'),
    
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

    path('api/booking/<int:booking_id>/get/', views.get_booking_for_edit, name='api_booking_get'),
    path('api/booking/<int:booking_id>/update/', views.api_update_booking, name='api_booking_update'),
    path('api/booking/<int:booking_id>/delete/', views.api_delete_booking, name='api_booking_delete'),
    
    # Дополнительные рабочие дни
    path('api/extra-days/add/', views.api_add_extra_day, name='api_add_extra_day'),
    path('api/extra-days/<int:extra_day_id>/delete/', views.api_delete_extra_day, name='api_delete_extra_day'),
    path('api/extra-days/delete-by-date/', views.api_delete_extra_day_by_date, name='api_delete_extra_day_by_date'),

    path('api/extra-days/upcoming/', views.get_extra_days_upcoming, name='api_extra_days_upcoming'),
    path('api/extra-days/past/', views.get_extra_days_past, name='api_extra_days_past'),

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
    path('api/clients/search/', views.search_clients_api, name='api_search_clients'),

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

    path('api/upload-avatar/', views.upload_avatar, name='upload_avatar'),

    path('api/blacklist/add/', views.api_blacklist_add, name='api_blacklist_add'),
    path('api/blacklist/<int:client_id>/delete/', views.api_blacklist_delete, name='api_blacklist_delete'),

    path('api/notifications/', views.get_notifications, name='api_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='api_mark_read'),
    path('api/notifications/<int:notification_id>/unread/', views.mark_notification_unread, name='api_mark_unread'),
    path('api/notifications/mark-all-read/', views.mark_all_read, name='api_mark_all_read'),

    path('api/<str:login>/book-multiple/', views.create_multiple_bookings, name='api_book_multiple'),

    path('api/support/messages/', views.get_support_messages, name='api_support_messages'),
    path('api/support/send/', views.send_support_message, name='api_support_send'),
    path('api/support/unread/', views.get_unread_support_count, name='api_support_unread'),


    
    
]