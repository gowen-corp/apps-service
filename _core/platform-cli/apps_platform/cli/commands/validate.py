"""
Command: platform validate [service_name]

Валидация конфигураций сервисов (статическая + runtime).
"""
from pathlib import Path

import typer
from rich.console import Console

from apps_platform.validators import StaticValidator, RuntimeValidator, ValidationReporter

app = typer.Typer()
console = Console()


@app.command()
def validate(
    service_name: str | None = typer.Argument(
        None,
        help="Имя сервиса для валидации. Если не указано, проверяются все сервисы.",
    ),
    runtime: bool = typer.Option(
        False, "--runtime", "-r", help="Выполнить runtime-проверки (контейнеры, health)"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Вывод в JSON формате (для CI)"
    ),
):
    """
    Валидация конфигураций сервисов.
    
    Проверяет корректность service.yml и docker-compose.yml перед деплоем:
    
    ✅ Статические проверки (всегда):
      - Парсинг YAML файлов
      - Наличие routing.container_name и internal_port
      - Соответствие visibility и директории (public/internal)
      - Наличие platform_network: external: true в compose
    
    🔍 Runtime проверки (с флагом --runtime):
      - Статус контейнеров
      - Принадлежность к platform_network
      - Health endpoint через docker run --network platform_network
    
    🛠 Генерирует готовые команды исправления при обнаружении ошибок.
    """
    # Импортируем функции из основного CLI модуля
    from apps_platform.cli import get_config, get_services, PROJECT_ROOT
    
    try:
        config = get_config()
    except typer.Exit:
        console.print("[red]❌ Конфигурация не найдена. Запустите ./install.sh или укажите OPS_CONFIG_PATH[/red]")
        raise typer.Exit(1)
    
    project_root = Path(config.get("project_root", str(PROJECT_ROOT)))
    services_path = config.get("services_path", "services")
    
    # Получаем список сервисов
    try:
        all_services = get_services()
    except Exception as e:
        console.print(f"[red]❌ Ошибка сканирования сервисов: {e}[/red]")
        raise typer.Exit(1)
    
    if not all_services:
        if json_output:
            console.print('{"message": "Нет данных", "results": {}}')
        else:
            console.print("⚪ Нет данных для валидации")
        raise typer.Exit(0)
    
    # Определяем, какие сервисы проверять
    if service_name:
        if service_name not in all_services:
            console.print(f"[red]❌ Сервис '{service_name}' не найден[/red]")
            available = ", ".join(all_services.keys())
            console.print(f"[yellow]Доступные сервисы: {available}[/yellow]")
            raise typer.Exit(1)
        services_to_check = {service_name: all_services[service_name]}
    else:
        services_to_check = all_services
    
    # Инициализируем валидаторы
    static_validator = StaticValidator(project_root, services_path)
    reporter = ValidationReporter(console)
    
    results = {}
    
    for svc_name, svc_info in services_to_check.items():
        svc_type = svc_info["type"]
        
        # Статическая валидация
        static_result = static_validator.validate_service(svc_name, svc_type)
        static_result["info"]["service_type"] = svc_type
        
        results[svc_name] = static_result
        
        # Runtime валидация (если запрошено)
        if runtime:
            compose_config = static_result.get("info", {}).get("compose_config", {})
            health_config = static_result.get("info", {}).get("service_config", {}).get("health", {})
            
            runtime_validator = RuntimeValidator(project_root, timeout=5)
            runtime_result = runtime_validator.validate_service(svc_name, compose_config)
            
            # Добавляем health_config в результат runtime
            runtime_result["health_config"] = health_config
            
            # Объединяем результаты
            results[svc_name]["errors"].extend(runtime_result.get("errors", []))
            results[svc_name]["warnings"].extend(runtime_result.get("warnings", []))
            results[svc_name]["info"].update(runtime_result.get("info", {}))
            
            # Обновляем ok статус
            if not runtime_result["ok"]:
                results[svc_name]["ok"] = False
    
    # Вывод результатов
    if json_output:
        console.print(reporter.format_json(results))
    elif service_name:
        # Один сервис - подробный вывод
        reporter.print_single_result(service_name, results[service_name], project_root)
    else:
        # Все сервисы - таблица
        reporter.print_report(results, project_root)
    
    # Exit code: 0 если нет ошибок, 1 если есть ошибки
    has_errors = any(r.get("errors") for r in results.values())
    raise typer.Exit(code=1 if has_errors else 0)


# Для совместимости с основным CLI
def register(parent_app: typer.Typer) -> None:
    """Регистрация команды в родительском приложении."""
    parent_app.add_typer(app, name="validate")
