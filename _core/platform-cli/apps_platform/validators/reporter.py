"""
Reporter module for validation results.
Formats output as Rich tables, JSON, and generates fix commands.
"""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table


class ValidationReporter:
    """Форматирование и вывод результатов валидации."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def format_table(self, results: dict) -> str:
        """
        Форматирование результатов валидации в виде таблицы Rich.

        Args:
            results: dict вида {service_name: {ok, errors, warnings, info}}

        Returns:
            Строка с отформатированной таблицей
        """
        table = Table(title="🔍 Результаты валидации сервисов", show_header=True)
        table.add_column("Сервис", style="cyan")
        table.add_column("Статус", style="bold")
        table.add_column("Ошибки", style="red")
        table.add_column("Предупреждения", style="yellow")

        for service_name, result in results.items():
            status_icon = "✅" if result["ok"] else "❌"
            status_text = f"{status_icon} OK" if result["ok"] else f"{status_icon} FAILED"

            errors_count = len(result.get("errors", []))
            warnings_count = len(result.get("warnings", []))

            errors_str = str(errors_count) if errors_count > 0 else "-"
            warnings_str = str(warnings_count) if warnings_count > 0 else "-"

            table.add_row(service_name, status_text, errors_str, warnings_str)

        # Сохраняем в строку через capture
        from io import StringIO

        output = StringIO()
        temp_console = Console(file=output, force_terminal=False)
        temp_console.print(table)

        # Добавляем детали по каждому сервису
        for service_name, result in results.items():
            if result["errors"] or result["warnings"]:
                output.write(f"\n[bold]{service_name}:[/bold]\n")

                if result["errors"]:
                    for error in result["errors"]:
                        output.write(f"  [red]✗[/red] {error}\n")

                if result["warnings"]:
                    for warning in result["warnings"]:
                        output.write(f"  [yellow]⚠[/yellow] {warning}\n")

        return output.getvalue()

    def format_json(self, results: dict) -> str:
        """Экспорт результатов в JSON формат."""
        # Определяем exit_code на основе наличия ошибок
        has_errors = any(r.get("errors", []) for r in results.values())
        output = {"exit_code": 1 if has_errors else 0, "results": results}
        return json.dumps(output, indent=2, ensure_ascii=False)

    def generate_fix_commands(self, results: dict, project_root: Path, services_path: str = "services") -> list[str]:
        """
        Генерация готовых команд для исправления ошибок.

        Returns:
            Список команд для исправления
        """
        commands = []

        for service_name, result in results.items():
            service_type = result.get("info", {}).get("service_type", "unknown")

            # Определяем путь к сервису
            if service_type == "core":
                service_dir = project_root / "_core" / service_name
            else:
                service_dir = project_root / services_path / service_type / service_name

            errors = result.get("errors", [])

            for error in errors:
                # Ошибка: отсутствует container_name в routing
                if "container_name" in error.lower() and "routing" in error.lower():
                    commands.append(
                        f"# Добавить container_name в {service_dir}/service.yml:\n"
                        f"# routing:\n"
                        f"#   - type: ...\n"
                        f"#     container_name: {service_name}\n"
                        f"#     internal_port: <port>"
                    )

                # Ошибка: отсутствует platform_network
                if "platform_network" in error.lower() and "отсутствует" in error.lower():
                    commands.append(
                        f"# Добавить сеть в {service_dir}/docker-compose.yml:\n"
                        f"# networks:\n"
                        f"#   platform_network:\n"
                        f"#     external: true\n"
                        f"#     name: platform_network"
                    )

                # Ошибка: visibility mismatch
                if "несоответствие" in error.lower() or "visibility" in error.lower():
                    commands.append(
                        f"# Исправить visibility в {service_dir}/service.yml или переместить сервис:\n"
                        f"# visibility: {'internal' if service_type == 'public' else 'public'}"
                    )

                # Ошибка: internal_port не число
                if "internal_port" in error.lower() and "числом" in error.lower():
                    commands.append(
                        f"# Исправить internal_port в {service_dir}/service.yml:\n"
                        f"# internal_port: 8000  # должно быть числом"
                    )

            # Предупреждения также могут требовать действий
            warnings = result.get("warnings", [])
            for warning in warnings:
                if "не задан 'container_name'" in warning:
                    commands.append(
                        f"# Рекомендуется добавить container_name в {service_dir}/docker-compose.yml:\n"
                        f"# services:\n"
                        f"#   {service_name}:\n"
                        f"#     container_name: {service_name}"
                    )

                if "должна быть external: true" in warning:
                    commands.append(
                        f"# Исправить конфигурацию сети в {service_dir}/docker-compose.yml:\n"
                        f"# networks:\n"
                        f"#   platform_network:\n"
                        f"#     external: true"
                    )

        return commands

    def print_report(self, results: dict, project_root: Path, show_json: bool = False) -> None:
        """
        Вывод полного отчёта о валидации.

        Args:
            results: результаты валидации
            project_root: корень проекта
            show_json: если True, выводить JSON вместо таблицы
        """
        if show_json:
            self.console.print(self.format_json(results))
        else:
            # Таблица
            self.console.print(self.format_table(results))

            # Блок с командами исправления
            fix_commands = self.generate_fix_commands(results, project_root)

            if fix_commands:
                self.console.print("\n[bold blue]🛠 Готовые команды для исправления:[/bold blue]\n")
                for cmd in fix_commands:
                    self.console.print(f"[dim]{cmd}[/dim]\n")

    def print_single_result(self, service_name: str, result: dict, project_root: Path) -> None:
        """Вывод результатов для одного сервиса."""
        status_icon = "✅" if result["ok"] else "❌"
        status_text = "OK" if result["ok"] else "FAILED"

        self.console.print(f"\n[bold]Сервис:[/bold] {service_name}")
        self.console.print(f"[bold]Статус:[/bold] {status_icon} {status_text}")

        if result.get("info", {}).get("service_dir"):
            self.console.print(f"[bold]Путь:[/bold] {result['info']['service_dir']}")

        if result["errors"]:
            self.console.print(f"\n[red][bold]Ошибки ({len(result['errors'])}):[/bold][/red]")
            for error in result["errors"]:
                self.console.print(f"  [red]✗[/red] {error}")

        if result["warnings"]:
            self.console.print(f"\n[yellow][bold]Предупреждения ({len(result['warnings'])}):[/bold][/yellow]")
            for warning in result["warnings"]:
                self.console.print(f"  [yellow]⚠[/yellow] {warning}")

        if not result["errors"] and not result["warnings"]:
            self.console.print("[green]✓ Нет проблем[/green]")

        # Команды исправления
        fix_commands = self.generate_fix_commands({service_name: result}, project_root)
        if fix_commands:
            self.console.print("\n[bold blue]🛠 Готовые команды для исправления:[/bold blue]")
            for cmd in fix_commands:
                self.console.print(f"[dim]{cmd}[/dim]")
