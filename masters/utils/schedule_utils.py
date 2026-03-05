from datetime import datetime, time, timedelta, date
from typing import List, Dict, Optional, Tuple
from ..models import Master, Schedule, DayOff, Booking, Service

class ScheduleCalculator:
    """Класс для расчета свободного времени мастера"""
    
    def __init__(self, master: Master):
        self.master = master
    
    def get_working_hours_for_date(self, target_date: date) -> Optional[Tuple[time, time]]:
        """
        Получает рабочие часы мастера на конкретную дату
        Возвращает (start_time, end_time) или None, если мастер не работает
        """
        # Проверяем, не выходной ли это день
        if DayOff.objects.filter(master=self.master, date=target_date).exists():
            return None
        
        # Получаем день недели (0 - понедельник, 6 - воскресенье)
        day_of_week = target_date.weekday()
        
        # Ищем расписание на этот день
        try:
            schedule = Schedule.objects.get(master=self.master, day_of_week=day_of_week)
            return (schedule.start_time, schedule.end_time)
        except Schedule.DoesNotExist:
            return None
    
    def get_booked_slots_for_date(self, target_date: date) -> List[Tuple[time, time]]:
        """
        Получает все занятые слоты на конкретную дату
        Возвращает список кортежей (start_time, end_time)
        """
        bookings = Booking.objects.filter(
            master=self.master,
            date=target_date,
            status='confirmed'  # только подтвержденные записи
        ).select_related('service')
        
        booked_slots = []
        for booking in bookings:
            # Вычисляем время окончания услуги
            start = booking.time
            duration_minutes = booking.service.duration
            end = (datetime.combine(date.today(), start) + 
                   timedelta(minutes=duration_minutes)).time()
            booked_slots.append((start, end))
        
        return booked_slots
    
    def generate_time_slots(self, 
                           target_date: date, 
                           service_duration: int,
                           slot_step: int = 15) -> List[Dict]:
        """
        Генерирует свободные слоты для конкретной даты и услуги
        
        Параметры:
        - target_date: дата для поиска
        - service_duration: длительность услуги в минутах
        - slot_step: шаг сетки времени (по умолчанию 15 минут)
        
        Возвращает список свободных слотов
        """
        # Получаем рабочие часы
        working_hours = self.get_working_hours_for_date(target_date)
        if not working_hours:
            return []
        
        start_work, end_work = working_hours
        
        # Получаем занятые слоты
        booked_slots = self.get_booked_slots_for_date(target_date)
        
        # Преобразуем время в минуты от начала дня для удобства
        def time_to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute
        
        start_minutes = time_to_minutes(start_work)
        end_minutes = time_to_minutes(end_work)
        
        # Создаем список всех возможных слотов с заданным шагом
        all_slots = []
        current = start_minutes
        
        while current + service_duration <= end_minutes:
            slot_start = current
            slot_end = current + service_duration
            
            # Проверяем, не пересекается ли слот с занятыми
            is_free = True
            for booked_start, booked_end in booked_slots:
                booked_start_min = time_to_minutes(booked_start)
                booked_end_min = time_to_minutes(booked_end)
                
                # Проверка пересечения интервалов
                if not (slot_end <= booked_start_min or slot_start >= booked_end_min):
                    is_free = False
                    # Перескакиваем на конец занятого слота
                    current = booked_end_min
                    break
            
            if is_free:
                # Добавляем свободный слот
                start_time = f"{slot_start // 60:02d}:{slot_start % 60:02d}"
                all_slots.append({
                    'start': start_time,
                    'end': f"{slot_end // 60:02d}:{slot_end % 60:02d}",
                    'start_minutes': slot_start,
                    'end_minutes': slot_end,
                    'display': f"{start_time}"
                })
                current += slot_step
            else:
                # Продолжаем проверку со следующей позиции
                continue
        
        return all_slots
    
    def get_available_dates(self, days_ahead: int = 30, min_service_duration: int = 30) -> List[date]:
        """
        Получает список дат, в которые есть свободные окна
        
        Параметры:
        - days_ahead: на сколько дней вперед смотреть
        - min_service_duration: минимальная длительность услуги для проверки
        """
        available_dates = []
        today = date.today()
        
        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            
            # Проверяем, работает ли мастер в этот день
            working_hours = self.get_working_hours_for_date(check_date)
            if not working_hours:
                continue
            
            # Проверяем, есть ли хотя бы один свободный слот
            slots = self.generate_time_slots(check_date, min_service_duration)
            if slots:
                available_dates.append(check_date)
        
        return available_dates