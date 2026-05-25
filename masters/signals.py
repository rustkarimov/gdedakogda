from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Master, Booking, Notification

@receiver(post_save, sender=User)
def create_master_profile(sender, instance, created, **kwargs):
    if created:
        Master.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_master_profile(sender, instance, **kwargs):
    if hasattr(instance, 'master'):
        instance.master.save()

@receiver(post_save, sender=Booking)
def create_booking_notification(sender, instance, created, **kwargs):
    print(f"🔔 Сигнал сработал! created={created}, created_by={getattr(instance, 'created_by', 'НЕТ ПОЛЯ')}")  # ← ВРЕМЕННО ДЛЯ ОТЛАДКИ
    
    if created:
        if hasattr(instance, 'created_by') and instance.created_by == 'client':
            notif = Notification.objects.create(
                master=instance.master,
                type='new_booking',
                title=f'Новая запись от {instance.client_name}',
                message=f'{instance.client_name} записался на {instance.service.name} {instance.date} в {instance.time}',
                content_object=instance
            )
            print(f"✅ Уведомление создано: {notif.id}")
        else:
            print(f"⚠️ Уведомление НЕ создано: created_by={getattr(instance, 'created_by', 'НЕТ ПОЛЯ')}")