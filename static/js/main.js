// Маска для российского телефона
function phoneMask(input) {
    // Убираем все не-цифры
    let value = input.value.replace(/\D/g, '');
    
    // Если поле пустое или начинается не с 7
    if (value.length === 0) {
        input.value = '';
        return;
    }
    
    // Если первая цифра не 7 или не 8, ставим 7
    if (value[0] !== '7' && value[0] !== '8') {
        value = '7' + value;
    }
    
    // Заменяем 8 на 7 (единый формат)
    if (value[0] === '8') {
        value = '7' + value.slice(1);
    }
    
    // Ограничиваем длину 11 цифрами
    if (value.length > 11) {
        value = value.slice(0, 11);
    }
    
    // Форматируем: 7 999 123-45-67
    let formatted = '';
    if (value.length > 0) {
        formatted = value[0];
        if (value.length > 1) {
            formatted += ' ' + value.slice(1, 4);
        }
        if (value.length > 4) {
            formatted += ' ' + value.slice(4, 7);
        }
        if (value.length > 7) {
            formatted += '-' + value.slice(7, 9);
        }
        if (value.length > 9) {
            formatted += '-' + value.slice(9, 11);
        }
    }
    
    input.value = formatted;
}

// Применяем маску ко всем полям телефона
document.addEventListener('DOMContentLoaded', function() {
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            phoneMask(this);
        });
    });
});