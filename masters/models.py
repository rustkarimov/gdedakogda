from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify  # <--- ДОБАВЬ ЭТУ СТРОКУ
from cryptography.fernet import Fernet
import os
import base64  # тоже может пригодиться

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils.text import slugify
from cryptography.fernet import Fernet
import random

# Кастомный менеджер пользователей
class CustomUserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Телефон обязателен')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone, password, **extra_fields)

# Кастомная модель пользователя (вход по телефону)
class CustomUser(AbstractUser):
    username = None
    phone = models.CharField(max_length=20, unique=True, verbose_name="Телефон")
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
    
    def __str__(self):
        return self.phone

# Модель мастера
class Master(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, verbose_name="Пользователь")
    phone = models.CharField(max_length=20, verbose_name="Телефон мастера")
    first_name = models.CharField(max_length=50, verbose_name="Имя", blank=True)
    last_name = models.CharField(max_length=50, verbose_name="Фамилия", blank=True)
    bio = models.TextField(verbose_name="О себе", blank=True)
    
    encryption_key = models.BinaryField(verbose_name="Ключ шифрования", null=True, blank=True, editable=False)
    slug = models.SlugField(unique=True, verbose_name="Ссылка", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Самозанятый мастер"
        verbose_name_plural = "Самозанятые мастера"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.user.phone
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.user.phone)
            slug = base_slug
            counter = 1
            while Master.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        if not self.encryption_key:
            self.generate_encryption_key()
            
        super().save(*args, **kwargs)
    
    def generate_encryption_key(self):
        key = Fernet.generate_key()
        self.encryption_key = key
        return key
    
    def get_encryption_key(self):
        return self.encryption_key

    
# Модель для кодов подтверждения
class PhoneVerification(models.Model):
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    code = models.CharField(max_length=6, verbose_name="Код подтверждения")
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Код подтверждения"
        verbose_name_plural = "Коды подтверждения"
    
    def __str__(self):
        return f"{self.phone} - {self.code}"

class Service(models.Model):
    """
    Услуги мастера
    """
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=100, verbose_name="Название услуги")
    description = models.TextField(verbose_name="Описание", blank=True)
    duration = models.IntegerField(verbose_name="Длительность (минут)", help_text="Например: 60, 90, 120")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Цена")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    
    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
    
    def __str__(self):
        return f"{self.name} ({self.duration} мин, {self.price} руб)"


class Schedule(models.Model):
    """
    Регулярное расписание (на неделю)
    """
    DAYS_OF_WEEK = [
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
        (5, 'Суббота'),
        (6, 'Воскресенье'),
    ]
    
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK, verbose_name="День недели")
    start_time = models.TimeField(verbose_name="Начало работы")
    end_time = models.TimeField(verbose_name="Конец работы")
    is_working = models.BooleanField(default=True, verbose_name="Рабочий день")
    
    class Meta:
        verbose_name = "Расписание"
        verbose_name_plural = "Расписание"
        unique_together = ['master', 'day_of_week']  # У мастера может быть только одно расписание на день
    
    def __str__(self):
        return f"{self.get_day_of_week_display()}: {self.start_time} - {self.end_time}"


class DayOff(models.Model):
    """
    Конкретные выходные дни (отпуск, отгулы)
    """
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name='days_off')
    date = models.DateField(verbose_name="Дата")
    reason = models.CharField(max_length=200, verbose_name="Причина", blank=True)
    
    class Meta:
        verbose_name = "Выходной день"
        verbose_name_plural = "Выходные дни"
        unique_together = ['master', 'date']  # Нельзя дважды отметить один день
    
    def __str__(self):
        return f"{self.date}: {self.reason or 'Выходной'}"


class Booking(models.Model):
    """
    Запись клиента
    """
    STATUS_CHOICES = [
        ('confirmed', 'Подтверждена'),
        ('cancelled', 'Отменена'),
        ('completed', 'Выполнена'),
    ]
    
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    
    # Данные клиента
    client_name = models.CharField(max_length=100, verbose_name="Имя клиента")
    encrypted_phone = models.BinaryField(verbose_name="Телефон (зашифрованный)")
    client_comment = models.TextField(verbose_name="Комментарий", blank=True)
    
    # Дата и время записи
    date = models.DateField(verbose_name="Дата записи")
    time = models.TimeField(verbose_name="Время записи")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed', verbose_name="Статус")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ['date', 'time']
        # Нельзя дважды записать на одно и то же время
        unique_together = ['master', 'date', 'time']
    
    def __str__(self):
        return f"{self.client_name} - {self.date} {self.time}"
    
    def get_decrypted_phone(self, key):
        """Расшифровывает телефон (будет использоваться мастером)"""
        f = Fernet(key)
        return f.decrypt(bytes(self.encrypted_phone)).decode()
