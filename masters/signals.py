from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Master

@receiver(post_save, sender=User)
def create_master_profile(sender, instance, created, **kwargs):
    """Создает профиль мастера ТОЛЬКО при создании нового пользователя"""
    if created:
        Master.objects.get_or_create(user=instance)  # используем get_or_create для безопасности

@receiver(post_save, sender=User)
def save_master_profile(sender, instance, **kwargs):
    """Сохраняет профиль мастера если он существует"""
    if hasattr(instance, 'master'):
        instance.master.save()