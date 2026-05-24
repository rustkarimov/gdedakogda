from datetime import datetime, time, timedelta, date
from typing import List, Dict, Optional, Tuple
from ..models import Master, Schedule, DayOff, Booking, Service, ExtraWorkingDay

class ScheduleCalculator:
    """Класс для расчета свободного времени мастера"""
    
    def __init__(self, master: Master):
        self.master = master

    def get_working_hours_for_date(self, target_date: date):
        """Получает рабочие часы мастера на конкретную дату с учетом приоритетов"""
        
        # 1. Проверяем выходные дни (высший приоритет)
        if DayOff.objects.filter(master=self.master, date=target_date).exists():
            return None
        
        # 2. Проверяем дополнительные рабочие дни
        extra_day = ExtraWorkingDay.objects.filter(master=self.master, date=target_date).first()
        if extra_day:
            return (extra_day.start_time, extra_day.end_time)
        
        # 3. Проверяем регулярное расписание
        day_of_week = target_date.weekday()
        schedule = Schedule.objects.filter(master=self.master, day_of_week=day_of_week).first()
        if schedule:
            return (schedule.start_time, schedule.end_time)
        
        return None
    
    
    def get_booked_slots_for_date(self, target_date: date):
        """Получает все занятые слоты на конкретную дату"""
        bookings = Booking.objects.filter(
            master=self.master,
            date=target_date,
            status='confirmed'
        ).select_related('service')
        
        def time_to_minutes(t):
            return t.hour * 60 + t.minute
        
        booked_slots = []
        for booking in bookings:
            start = booking.time
            end = (datetime.combine(date.today(), start) + 
                timedelta(minutes=booking.service.duration)).time()
            booked_slots.append((start, end, booking.id))
        
        return booked_slots
    
    def generate_time_slots(self, target_date: date, service_duration: int, slot_step: int = 15, exclude_booking_id: int = None):
        """Генерирует свободные слоты"""
        working_hours = self.get_working_hours_for_date(target_date)
        if not working_hours:
            return []
        
        start_work, end_work = working_hours
        
        def time_to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute
        
        start_minutes = time_to_minutes(start_work)
        end_minutes = time_to_minutes(end_work)
        
        # Получаем перерывы ТОЛЬКО из актуального источника
        # Приоритет: ExtraWorkingDay (даже без перерывов) > Schedule
        extra_day = ExtraWorkingDay.objects.filter(master=self.master, date=target_date).first()
        schedule = None
        
        if not extra_day:
            day_of_week = target_date.weekday()
            schedule = Schedule.objects.filter(master=self.master, day_of_week=day_of_week).first()
        
        breaks = []
        if extra_day:
            # Берём перерывы из дополнительного дня (даже если их нет — значит, нет перерывов)
            breaks = [(time_to_minutes(b.start_time), time_to_minutes(b.end_time)) 
                    for b in extra_day.breaks.all()]
        elif schedule:
            # Берём перерывы из регулярного расписания
            breaks = [(time_to_minutes(b.start_time), time_to_minutes(b.end_time)) 
                    for b in schedule.breaks.all()]
        # Если нет ни extra_day, ни schedule — breaks остаётся пустым
        
        # Получаем занятые слоты
        booked_slots = []
        for booking in Booking.objects.filter(
            master=self.master,
            date=target_date,
            status='confirmed'
        ).select_related('service'):
            if exclude_booking_id and booking.id == exclude_booking_id:
                continue
            start = time_to_minutes(booking.time)
            end = start + booking.service.duration
            booked_slots.append((start, end))
        
        # Массив занятых минут
        busy_minutes = [False] * (24 * 60)
        
        # Отмечаем перерывы
        for b_start, b_end in breaks:
            for m in range(b_start, min(b_end, 1440)):
                busy_minutes[m] = True
        
        # Отмечаем занятые слоты
        for b_start, b_end in booked_slots:
            for m in range(b_start, min(b_end, 1440)):
                busy_minutes[m] = True
        
        # Генерируем слоты
        all_slots = []
        current = start_minutes
        
        while current + service_duration <= end_minutes:
            slot_start = current
            slot_end = current + service_duration
            
            # Проверяем, свободен ли весь слот
            slot_busy = False
            for m in range(slot_start, slot_end):
                if m < 1440 and busy_minutes[m]:
                    slot_busy = True
                    current = m + 1
                    break
            
            if not slot_busy:
                start_time = f"{slot_start // 60:02d}:{slot_start % 60:02d}"
                all_slots.append({
                    'start': start_time,
                    'end': f"{slot_end // 60:02d}:{slot_end % 60:02d}",
                    'start_minutes': slot_start,
                    'end_minutes': slot_end,
                    'display': start_time
                })
                current += slot_step
            # если слот занят, current уже обновлён
        
        return all_slots


    def get_available_dates(self, days_ahead: int = 60, min_service_duration: int = 30) -> List[date]:
        """Получает список дат, в которые есть свободные окна"""
        available_dates = []
        today = date.today()
        
        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            
            # Проверяем, работает ли мастер в этот день (учитывает выходные)
            working_hours = self.get_working_hours_for_date(check_date)
            if not working_hours:
                continue
            
            # Проверяем, есть ли хотя бы один свободный слот
            slots = self.generate_time_slots(check_date, min_service_duration)
            if slots:
                available_dates.append(check_date)
        
        return available_dates