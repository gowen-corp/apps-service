"""Компонент карточки сервиса."""
from nicegui import ui
from typing import Optional, Callable
from app.services.discovery import ServiceManifest


class ServiceCard(ui.card):
    """Карточка сервиса для отображения в списке."""

    def __init__(self, service: ServiceManifest,
                 on_view: Optional[Callable] = None,
                 on_deploy: Optional[Callable] = None,
                 on_restart: Optional[Callable] = None,
                 on_stop: Optional[Callable] = None):
        """Инициализация карточки сервиса.
        
        Args:
            service: Объект сервиса
            on_view: Callback для просмотра деталей
            on_deploy: Callback для деплоя
            on_restart: Callback для перезапуска
            on_stop: Callback для остановки
        """
        super().__init__()
        
        self._service = service
        self._on_view = on_view
        self._on_deploy = on_deploy
        self._on_restart = on_restart
        self._on_stop = on_stop
        
        self._props['flat'] = True
        self._props['bordered'] = True
        self.classes('w-full p-4')
        
        self._render()

    def _render(self):
        """Рендер содержимого карточки."""
        with self:
            with ui.row().classes('w-full items-center gap-4'):
                # Индикатор статуса
                self._render_status_indicator()
                
                # Основная информация
                self._render_info()
                
                # Видимость
                self._render_visibility_chip()
                
                # Кнопки действий
                self._render_actions()

    def _render_status_indicator(self):
        """Рендер индикатора статуса."""
        status_config = {
            'running': {'icon': 'play_circle', 'color': 'positive'},
            'stopped': {'icon': 'stop_circle', 'color': 'negative'},
            'partial': {'icon': 'remove_circle', 'color': 'warning'},
            'unknown': {'icon': 'help_circle', 'color': 'grey'},
        }
        
        config = status_config.get(self._service.status, status_config['unknown'])
        
        with ui.column().classes('items-center w-10'):
            ui.icon(config['icon']).classes(f'text-2xl text-{config["color"]}')

    def _render_info(self):
        """Рендер основной информации."""
        with ui.column().classes('flex-1'):
            # Название
            name = self._service.display_name or self._service.name
            ui.label(name).classes('text-subtitle1 font-medium')
            
            # Маршруты
            routing = self._format_routing()
            if routing:
                ui.label(routing).classes('text-caption text-grey-7')
            
            # Версия
            if self._service.version:
                ui.label(f'v{self._service.version}').classes('text-xs text-grey-5')

    def _render_visibility_chip(self):
        """Рендер метки видимости."""
        is_public = self._service.visibility == 'public'
        chip = ui.chip(
            'Публичный' if is_public else 'Внутренний',
            icon='public' if is_public else 'lock'
        )
        chip.props(f'color={"info" if is_public else "secondary"}')

    def _render_actions(self):
        """Рендер кнопок действий."""
        with ui.row().classes('gap-1'):
            # Просмотр
            ui.button(
                icon='visibility',
                on_click=lambda: self._on_view(self._service) if self._on_view else None
            ).props('flat dense round').tooltip('Просмотр')
            
            # Перезапуск
            ui.button(
                icon='refresh',
                on_click=lambda: self._on_restart(self._service) if self._on_restart else None
            ).props('flat dense round').tooltip('Перезапустить')
            
            # Старт/Стоп
            if self._service.status == 'running':
                ui.button(
                    icon='stop_circle',
                    on_click=lambda: self._on_stop(self._service) if self._on_stop else None
                ).props('flat dense round').classes('text-negative').tooltip('Остановить')
            else:
                ui.button(
                    icon='play_circle',
                    on_click=lambda: self._on_deploy(self._service) if self._on_deploy else None
                ).props('flat dense round').classes('text-positive').tooltip('Запустить')

    def _format_routing(self) -> str:
        """Форматирование информации о маршрутизации."""
        if not self._service.routing:
            return ''
        
        parts = []
        for route in self._service.routing:
            if route.type == 'domain':
                parts.append(route.domain)
            elif route.type == 'subfolder':
                parts.append(f'{route.base_domain}{route.path}')
            elif route.type == 'port':
                parts.append(f':{route.port}')
        
        return ' • '.join(parts) if parts else ''

    def update_status(self, status: str):
        """Обновление статуса сервиса.
        
        Args:
            status: Новый статус
        """
        self._service.status = status
        # Перерисовка карточки
        self.clear()
        self._render()


def create_service_card(service: ServiceManifest,
                        on_view: Optional[Callable] = None,
                        on_deploy: Optional[Callable] = None,
                        on_restart: Optional[Callable] = None,
                        on_stop: Optional[Callable] = None) -> ServiceCard:
    """Фабричная функция для создания карточки сервиса.
    
    Args:
        service: Объект сервиса
        on_view: Callback для просмотра
        on_deploy: Callback для деплоя
        on_restart: Callback для перезапуска
        on_stop: Callback для остановки
        
    Returns:
        Экземпляр ServiceCard
    """
    return ServiceCard(
        service=service,
        on_view=on_view,
        on_deploy=on_deploy,
        on_restart=on_restart,
        on_stop=on_stop
    )
