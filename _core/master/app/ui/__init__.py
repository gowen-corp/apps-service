"""UI модуль Platform Manager."""
from app.ui.main_page import render_main_page
from app.ui.services_page import render_services_page
from app.ui.logs_page import render_logs_page
from app.ui.backups_page import render_backups_page

__all__ = [
    'render_main_page',
    'render_services_page',
    'render_logs_page',
    'render_backups_page',
]
