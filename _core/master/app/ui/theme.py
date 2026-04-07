"""Модуль тем и стилей для UI Platform Manager.

Этот модуль определяет единую цветовую схему и стили для всех страниц.
Используется сдержанная цветовая палитра для снижения визуального шума.
"""
from nicegui import ui


# Цветовая палитра
COLORS = {
    # Основные цвета
    'primary': '#1976d2',      # Синий
    'secondary': '#424242',    # Серый
    
    # Семантические цвета
    'positive': '#2e7d32',     # Зеленый
    'negative': '#d32f2f',     # Красный
    'warning': '#ed6c02',      # Оранжевый
    'info': '#0288d1',         # Голубой
    
    # Фоновые цвета
    'bg-light': '#fafafa',
    'bg-card': '#ffffff',
    'bg-hover': '#f5f5f5',
    
    # Текст
    'text-primary': '#212121',
    'text-secondary': '#757575',
    'text-disabled': '#9e9e9e',
}


def apply_theme() -> None:
    """Применение единой темы ко всему приложению.
    
    Вызывается один раз при старте приложения.
    """
    # Настраиваем Quasar тему
    ui.query('body').classes('bg-grey-1')
    
    # Добавляем кастомные стили
    ui.add_css('''
        /* Общие стили */
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        /* Карточки */
        .q-card {
            border-radius: 8px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        }
        
        /* Кнопки */
        .q-btn {
            border-radius: 6px !important;
            text-transform: none !important;
            font-weight: 500 !important;
        }
        
        /* Таблицы */
        .q-table {
            border-radius: 8px !important;
        }
        .q-table thead tr {
            background-color: #f5f5f5 !important;
        }
        
        /* Инпуты */
        .q-field--outlined .q-field__control {
            border-radius: 6px !important;
        }
        
        /* Чипы */
        .q-chip {
            border-radius: 6px !important;
            font-weight: 500 !important;
        }
        
        /* Уведомления */
        .q-notification {
            border-radius: 8px !important;
        }
        
        /* Скрываем излишние тени */
        .q-header {
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }
    ''')


def get_card_classes() -> str:
    """Возвращает стандартные классы для карточек.
    
    Returns:
        Строка с CSS классами
    """
    return 'p-4 bg-card rounded shadow-sm'


def get_button_classes(color: str = 'default', flat: bool = True) -> str:
    """Возвращает стандартные классы для кнопок.
    
    Args:
        color: Цвет кнопки
        flat: Плоский стиль
        
    Returns:
        Строка с CSS классами
    """
    classes = 'rounded'
    if flat:
        classes += ' q-btn-flat'
    return classes


def get_input_classes() -> str:
    """Возвращает стандартные классы для полей ввода.
    
    Returns:
        Строка с CSS классами
    """
    return 'rounded'
