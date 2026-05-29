from django.contrib import admin
from django import forms
from django.utils.text import slugify
from .models import Master, Service, Schedule, DayOff, Booking, PhoneVerification, CustomUser, SupportMessage

from django.contrib.auth.admin import UserAdmin

from django.urls import reverse
from django.utils.html import format_html

# Кастомная админка для CustomUser
class CustomUserAdmin(UserAdmin):
    list_display = ('phone', 'first_name', 'last_name', 'is_staff')
    search_fields = ('phone', 'first_name', 'last_name')
    ordering = ('phone',)
    
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2'),
        }),
    )

# Регистрируем кастомную модель пользователя
admin.site.register(CustomUser, CustomUserAdmin)

# Форма для мастера
class MasterAdminForm(forms.ModelForm):
    class Meta:
        model = Master
        fields = '__all__'
        widgets = {
            'slug': forms.TextInput(attrs={'readonly': 'readonly'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False

# Инлайн для мастера (если нужно привязать к пользователю)
class MasterInline(admin.StackedInline):
    model = Master
    can_delete = False
    verbose_name_plural = 'Профиль мастера'
    fields = ['phone', 'first_name', 'last_name', 'bio', 'login', 'encryption_key']
    readonly_fields = ['encryption_key']
    extra = 0
    max_num = 1

# Админка мастера
@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'public_slug', 'created_at']  # замени slug на public_slug
    list_filter = ['created_at']
    search_fields = ['user__phone', 'phone', 'first_name', 'last_name', 'login']  # добавил login
    readonly_fields = ['encryption_key', 'created_at', 'updated_at']
    fields = ['user', 'phone', 'first_name', 'last_name', 'bio', 'login', 'encryption_key', 'created_at', 'updated_at']
    
    def full_name(self, obj):
        return obj.__str__()
    full_name.short_description = "Имя мастера"
    
    def public_slug(self, obj):
        return obj.public_slug
    public_slug.short_description = "Ссылка"

# Админка услуг
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'master', 'duration', 'price', 'is_active']
    list_filter = ['master', 'is_active']
    search_fields = ['name', 'master__first_name', 'master__last_name']

# Админка расписания
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['master', 'day_of_week', 'start_time', 'end_time']
    list_filter = ['master']

# Админка выходных дней
@admin.register(DayOff)
class DayOffAdmin(admin.ModelAdmin):
    list_display = ['master', 'date', 'reason']
    list_filter = ['master', 'date']

# Админка записей
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'master', 'service', 'date', 'time', 'status']
    list_filter = ['master', 'status', 'date']
    search_fields = ['client_name', 'master__first_name', 'master__last_name']
    readonly_fields = ['encrypted_phone']

# Админка кодов подтверждения
@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ['phone', 'code', 'created_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['phone', 'code']
    readonly_fields = ['created_at']
    
    
    
# admin.py
from django.contrib import admin
from .models import Notification, Master

from django.contrib import admin
from .models import Notification, Master

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['master', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'master__phone']
    actions = ['send_to_all_masters', 'send_to_selected_masters']
    
    def send_to_all_masters(self, request, queryset):
        count = 0
        for master in Master.objects.all():
            for notification in queryset:
                Notification.objects.create(
                    master=master,
                    type=notification.type,
                    title=notification.title,
                    message=notification.message
                )
                count += 1
        self.message_user(request, f'✅ Уведомления отправлены всем мастерам ({count})')
    send_to_all_masters.short_description = '📢 Отправить ВСЕМ мастерам'
    
    def send_to_selected_masters(self, request, queryset):
        # Получаем выбранных мастеров из POST
        master_ids = request.POST.getlist('_selected_action')
        masters = Master.objects.filter(id__in=master_ids)
        count = 0
        for master in masters:
            for notification in queryset:
                Notification.objects.create(
                    master=master,
                    type=notification.type,
                    title=notification.title,
                    message=notification.message
                )
                count += 1
        self.message_user(request, f'✅ Уведомления отправлены выбранным мастерам ({count})')
    send_to_selected_masters.short_description = '📢 Отправить ВЫБРАННЫМ мастерам'


from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.template.response import TemplateResponse
from .models import SupportMessage, Master

# Кастомное представление для чата поддержки
def support_chat_view(request):
    masters = Master.objects.all().order_by('-created_at')
    
    for master in masters:
        master.unread_count = SupportMessage.objects.filter(
            master=master, direction='user', is_read=False
        ).count()
        master.last_message = SupportMessage.objects.filter(master=master).order_by('-created_at').first()
    
    selected_master_id = request.GET.get('master_id')
    selected_master = None
    messages_list = []
    
    if selected_master_id:
        selected_master = get_object_or_404(Master, id=selected_master_id)
        messages_list = SupportMessage.objects.filter(master=selected_master).order_by('created_at')
        # Отмечаем сообщения от пользователя как прочитанные
        SupportMessage.objects.filter(master=selected_master, direction='user', is_read=False).update(is_read=True)
    
    if request.method == 'POST' and selected_master:
        reply_text = request.POST.get('reply_text', '').strip()
        if reply_text:
            SupportMessage.objects.create(
                master=selected_master,
                direction='admin',
                message=reply_text,
                is_read=False
            )
            messages.success(request, f'Ответ отправлен мастеру {selected_master.first_name}')
            return redirect(f'/admin/support-chat/?master_id={selected_master.id}')
    
    context = {
        'masters': masters,
        'selected_master': selected_master,
        'messages': messages_list,
        'title': 'Чат поддержки',
    }
    return TemplateResponse(request, 'admin/support_chat.html', context)


# Добавляем URL в админку
admin_urls = admin.site.get_urls()

def get_admin_urls():
    return [
        path('support-chat/', admin.site.admin_view(support_chat_view), name='support-chat'),
    ] + admin_urls

admin.site.get_urls = get_admin_urls



