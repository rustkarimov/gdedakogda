// ============================================================
// Модуль множественного выбора услуг
// ============================================================
const MultiService = {
    selectedServices: [],
    currentTotalDuration: 0,
    onServicesChange: null,
    
    // Добавить услугу
    add(serviceId, serviceName, serviceDuration, servicePrice) {
        if (this.selectedServices.some(s => s.id === serviceId)) {
            this.showMessage('Эта услуга уже добавлена', 'warning');
            return false;
        }
        
        this.selectedServices.push({
            id: serviceId,
            name: serviceName,
            duration: serviceDuration,
            price: servicePrice
        });
        
        this.update();
        return true;
    },
    
    // Удалить услугу по индексу
    remove(index) {
        this.selectedServices.splice(index, 1);
        this.update();
    },
    
    // Очистить всё
    clear() {
        this.selectedServices = [];
        this.update();
    },
    
    // Получить общую длительность
    getTotalDuration() {
        return this.selectedServices.reduce((sum, s) => sum + s.duration, 0);
    },
    
    // Получить общую цену
    getTotalPrice() {
        return this.selectedServices.reduce((sum, s) => sum + s.price, 0);
    },
    
    // Есть ли выбранные услуги
    hasServices() {
        return this.selectedServices.length > 0;
    },
    
    // Обновить UI корзины
    update() {
        this.currentTotalDuration = this.getTotalDuration();
        
        if (this.onServicesChange) {
            this.onServicesChange(this.selectedServices, this.currentTotalDuration);
        }
    },
    
    // Показать сообщение (адаптер под разные страницы)
    showMessage(message, type) {
        if (typeof showStyledAlert === 'function') {
            showStyledAlert(message, type);
        } else if (typeof showAlert === 'function') {
            showAlert(message, type === 'error' ? 'Ошибка' : 'Уведомление');
        } else {
            alert(message);
        }
    },
    
    // Рендер корзины (переопределяется на каждой странице)
    renderCart(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        if (this.selectedServices.length === 0) {
            container.closest('.services-cart')?.setAttribute('style', 'display: none');
            return;
        }
        
        container.closest('.services-cart')?.setAttribute('style', 'display: block');
        
        let html = '';
        this.selectedServices.forEach((service, index) => {
            html += `
                <div class="cart-item d-flex justify-content-between align-items-center mb-2 p-2 bg-light rounded">
                    <div>
                        <strong>${this.escapeHtml(service.name)}</strong>
                        <span class="text-muted ms-2">${service.duration} мин / ${service.price} ₽</span>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="MultiService.remove(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });
        
        html += `
            <div class="cart-total mt-2 pt-2 border-top">
                <div class="d-flex justify-content-between">
                    <strong>Итого:</strong>
                    <strong>${this.getTotalDuration()} мин / ${this.getTotalPrice()} ₽</strong>
                </div>
            </div>
            <div class="mt-2">
                <button class="btn btn-sm btn-outline-secondary w-100" onclick="MultiService.clear()">
                    <i class="fas fa-trash-alt me-1"></i>Очистить все
                </button>
            </div>
        `;
        
        container.innerHTML = html;
    },
    
    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : m === '<' ? '&lt;' : m === '>' ? '&gt;' : m);
    }
};