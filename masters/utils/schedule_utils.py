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
        """Получает все занятые слоты на конкретную дату с ID записи"""
        bookings = Booking.objects.filter(
            master=self.master,
            date=target_date,
            status='confirmed'
        ).select_related('service')
        
        booked_slots = []
        for booking in bookings:
            start = booking.time
            duration_minutes = booking.service.duration
            end = (datetime.combine(date.today(), start) + 
                timedelta(minutes=duration_minutes)).time()
            booked_slots.append((start, end, booking.id))  # добавляем ID
        return booked_slots
    
    def generate_time_slots(self, target_date: date, service_duration: int, slot_step: int = 15, exclude_booking_id: int = None, current_time: time = None, original_booking_id: int = None):
        """Генерирует свободные слоты с учётом перерывов, занятых записей и текущего времени
        
        Args:
            target_date: дата
            service_duration: длительность услуги в минутах
            slot_step: шаг сетки в минутах
            exclude_booking_id: ID записи, которую нужно исключить из проверки (при редактировании)
            current_time: текущее время (для сегодняшнего дня)
            original_booking_id: ID исходной записи, время которой нужно временно разблокировать (если меняется услуга)
        """
        
        working_hours = self.get_working_hours_for_date(target_date)
        if not working_hours:
            return []
        
        start_work, end_work = working_hours
        
        def time_to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute
        
        start_minutes = time_to_minutes(start_work)
        end_minutes = time_to_minutes(end_work)
        
        # Если передан current_time (для сегодняшнего дня), начинаем с текущего времени
        if current_time:
            current_minutes = time_to_minutes(current_time)
            # Округляем до следующего 15-минутного интервала
            current_minutes = ((current_minutes + slot_step - 1) // slot_step) * slot_step
            start_minutes = max(start_minutes, current_minutes)
        
        # Если старт больше или равен концу — слотов нет
        if start_minutes >= end_minutes:
            return []
        
        # Получаем перерывы в минутах
        day_of_week = target_date.weekday()
        schedule = Schedule.objects.filter(master=self.master, day_of_week=day_of_week).first()
        
        breaks = []
        if schedule:
            for break_start, break_end in schedule.breaks.all().values_list('start_time', 'end_time'):
                breaks.append((time_to_minutes(break_start), time_to_minutes(break_end)))
        
        # Получаем занятые слоты в минутах (исключая текущую запись при редактировании)
        booked_slots = []
        for start, end, booking_id in self.get_booked_slots_for_date(target_date):
            if exclude_booking_id and booking_id == exclude_booking_id:
                continue
            booked_slots.append((time_to_minutes(start), time_to_minutes(end)))
        
        # ========== НОВАЯ ЛОГИКА: временно разблокируем исходную запись ==========
        if original_booking_id:
            try:
                from ..models import Booking
                original_booking = Booking.objects.get(id=original_booking_id, master=self.master)
                original_start = time_to_minutes(original_booking.time)
                original_service = original_booking.service
                original_duration = original_service.duration
                original_end = original_start + original_duration
                
                # Удаляем из booked_slots диапазон исходной записи (с допуском 1 минута)
                booked_slots = [
                    (s, e) for (s, e) in booked_slots 
                    if not (abs(s - original_start) <= 1 and abs(e - original_end) <= 1)
                ]
                
                # Для отладки - выведем в консоль (временно)
                print(f"🔓 Разблокирован диапазон {original_start}-{original_end} для записи #{original_booking_id}")
                print(f"📋 Осталось заблокированных слотов: {len(booked_slots)}")
                
            except Booking.DoesNotExist:
                print(f"⚠️ Запись #{original_booking_id} не найдена")
                pass
        # ================================================================
        
        # Создаем массив занятых минут
        busy_minutes = [False] * (24 * 60)
        
        # Отмечаем перерывы
        for b_start, b_end in breaks:
            for m in range(b_start, b_end):
                if m < 1440:
                    busy_minutes[m] = True
        
        # Отмечаем занятые слоты
        for b_start, b_end in booked_slots:
            for m in range(b_start, b_end):
                if m < 1440:
                    busy_minutes[m] = True
        
        # Генерируем слоты
        all_slots = []
        current = start_minutes
        
        while current + service_duration <= end_minutes:
            slot_start = current
            slot_end = current + service_duration
            
            # Проверяем, свободен ли весь слот
            is_free = True
            for m in range(slot_start, slot_end):
                if m < 1440 and busy_minutes[m]:
                    is_free = False
                    # Перепрыгиваем на конец занятого блока
                    m_end = m
                    while m_end < 1440 and busy_minutes[m_end]:
                        m_end += 1
                    current = m_end
                    break
            
            if is_free:
                start_time = f"{slot_start // 60:02d}:{slot_start % 60:02d}"
                all_slots.append({
                    'start': start_time,
                    'end': f"{slot_end // 60:02d}:{slot_end % 60:02d}",
                    'start_minutes': slot_start,
                    'end_minutes': slot_end,
                    'display': start_time,
                    'id': len(all_slots)
                })
                current += slot_step
            # else: current уже обновлён в цикле
        
        return all_slots


    def get_available_dates(self, days_ahead: int = 60, min_service_duration: int = 30) -> List[date]:
        """Получает список дат, в которые есть свободные окна (с учётом текущего времени)"""
        available_dates = []
        today = date.today()
        now = datetime.now().time()
        
        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            
            # Проверяем, работает ли мастер в этот день
            working_hours = self.get_working_hours_for_date(check_date)
            if not working_hours:
                continue
            
            # Для сегодняшней даты передаём текущее время, чтобы не показывать прошедшие слоты
            current_time = now if check_date == today else None
            
            # Проверяем, есть ли хотя бы один свободный слот
            slots = self.generate_time_slots(
                check_date, 
                min_service_duration,
                current_time=current_time  # передаём текущее время
            )
            if slots:
                available_dates.append(check_date)
        
        return available_dates