from django.contrib import admin
from django import forms
from django.utils.text import slugify
from .models import Master, Service, Schedule, DayOff, Booking
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

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
        # Добавим подсказку
        if self.instance and self.instance.pk and not self.instance.slug:
            self.fields['slug'].help_text = "Заполнится автоматически при сохранении"

class MasterInline(admin.StackedInline):
    model = Master
    can_delete = False
    verbose_name_plural = 'Профиль самозанятого'
    form = MasterAdminForm
    fields = ['phone', 'first_name', 'last_name', 'bio', 'slug', 'encryption_key']
    readonly_fields = ['encryption_key']
    # Важно: не создаем новый профиль, если его нет
    extra = 0
    max_num = 1

class CustomUserAdmin(UserAdmin):
    inlines = [MasterInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff']
    
    def save_related(self, request, form, formsets, change):
        """Переопределяем сохранение связанных объектов"""
        super().save_related(request, form, formsets, change)
        # После сохранения пользователя, убеждаемся что у него есть мастер
        user = form.instance
        Master.objects.get_or_create(user=user)

# Перерегистрируем модель User
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    form = MasterAdminForm
    list_display = ['full_name', 'phone', 'slug', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'phone', 'first_name', 'last_name']
    readonly_fields = ['encryption_key', 'created_at', 'updated_at']
    fields = ['user', 'phone', 'first_name', 'last_name', 'bio', 'slug', 'encryption_key', 'created_at', 'updated_at']
    
    def full_name(self, obj):
        return obj.__str__()
    full_name.short_description = "Имя мастера"
    
    def save_model(self, request, obj, form, change):
        """При сохранении через админку мастера"""
        if not obj.slug:
            from django.utils.text import slugify
            base_slug = slugify(obj.user.username)
            slug = base_slug
            counter = 1
            while Master.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            obj.slug = slug
        super().save_model(request, obj, form, change)

# ... остальные админки без изменений ...
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'master', 'duration', 'price', 'is_active']
    list_filter = ['master', 'is_active']
    search_fields = ['name', 'master__first_name', 'master__last_name']

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['master', 'day_of_week', 'start_time', 'end_time']
    list_filter = ['master']

@admin.register(DayOff)
class DayOffAdmin(admin.ModelAdmin):
    list_display = ['master', 'date', 'reason']
    list_filter = ['master', 'date']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'master', 'service', 'date', 'time', 'status']
    list_filter = ['master', 'status', 'date']
    search_fields = ['client_name', 'master__first_name', 'master__last_name']
    readonly_fields = ['encrypted_phone']
