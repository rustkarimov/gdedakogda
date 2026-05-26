print("🔔 SIGNALS.PY ЗАГРУЖАЕТСЯ...")

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Master, Booking, Notification

print("🔔 SIGNALS.PY ЗАГРУЗИЛСЯ УСПЕШНО")

@receiver(post_save, sender=User)
def create_master_profile(sender, instance, created, **kwargs):
    print(f"👤 Сигнал User: created={created}, user={instance}")
    if created:
        Master.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_master_profile(sender, instance, **kwargs):
    if hasattr(instance, 'master'):
        instance.master.save()

@receiver(post_save, sender=Booking)
def create_booking_notification(sender, instance, created, **kwargs):
    print(f"📅 Сигнал: created={created}, created_by={instance.created_by}, id={instance.id}")
    if created and instance.created_by == 'client':
        print("✅ СОЗДАЁМ УВЕДОМЛЕНИЕ")
        Notification.objects.create(
            master=instance.master,
            type='new_booking',
            title=f'Новая запись от {instance.client_name}',
            message=f'{instance.client_name} записался на {instance.service.name} {instance.date} в {instance.time}',
            content_object=instance
        )
    else:
        print(f"❌ Условие НЕ выполнено: created={created}, created_by={instance.created_by}")


# from django.db.models.signals import post_save
# from django.contrib.auth.models import User
# from django.dispatch import receiver
# from .models import Master, Booking, Notification

# @receiver(post_save, sender=User)
# def create_master_profile(sender, instance, created, **kwargs):
#     if created:
#         Master.objects.get_or_create(user=instance)

# @receiver(post_save, sender=User)
# def save_master_profile(sender, instance, **kwargs):
#     if hasattr(instance, 'master'):
#         instance.master.save()

# @receiver(post_save, sender=Booking)
# def create_booking_notification(sender, instance, created, **kwargs):
#     print(f"🔔 Сигнал: created={created}, created_by={instance.created_by}")  # ← ВРЕМЕНН
#     if created and instance.created_by == 'client':  # только если запись создал клиент
#         Notification.objects.create(
#             master=instance.master,
#             type='new_booking',
#             title=f'Новая запись от {instance.client_name}',
#             message=f'{instance.client_name} записался на {instance.service.name} {instance.date} в {instance.time}',
#             content_object=instance
#         )