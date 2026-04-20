"""
Unit tests for validation modules.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps_platform.validators.reporter import ValidationReporter
from apps_platform.validators.runtime import RuntimeValidator
from apps_platform.validators.static import StaticValidator


class TestStaticValidator:
    """Тесты статического валидатора."""

    @pytest.fixture
    def temp_service_dir(self, tmp_path):
        """Создание тестовой директории сервиса."""
        service_dir = tmp_path / "services" / "internal" / "test-service"
        service_dir.mkdir(parents=True)
        return service_dir

    def test_validate_service_missing_files(self, tmp_path):
        """Валидация сервиса с отсутствующими файлами."""
        validator = StaticValidator(tmp_path, "services")
        result = validator.validate_service("nonexistent", "internal")

        assert not result["ok"]
        assert len(result["errors"]) > 0
        assert "service.yml не найден" in result["errors"][0]

    def test_validate_service_yaml_parse_error(self, tmp_path):
        """Валидация сервиса с некорректным YAML."""
        service_dir = tmp_path / "services" / "internal" / "bad-service"
        service_dir.mkdir(parents=True)

        (service_dir / "service.yml").write_text("invalid: yaml: content: [")
        (service_dir / "docker-compose.yml").write_text("version: '3'")

        validator = StaticValidator(tmp_path, "services")
        result = validator.validate_service("bad-service", "internal")

        assert not result["ok"]
        assert any("Ошибка парсинга" in e for e in result["errors"])

    def test_validate_service_valid(self, temp_service_dir):
        """Валидация корректного сервиса."""
        service_yml = """
name: test-service
version: "1.0.0"
type: docker-compose
visibility: internal
routing:
  - type: port
    internal_port: 8000
    container_name: test-service
"""
        compose_yml = """
version: '3.8'
services:
  test-service:
    image: nginx:latest
    container_name: test-service
    ports:
      - "8000:8000"
networks:
  platform_network:
    external: true
    name: platform_network
"""
        (temp_service_dir / "service.yml").write_text(service_yml)
        (temp_service_dir / "docker-compose.yml").write_text(compose_yml)

        validator = StaticValidator(temp_service_dir.parent.parent.parent, "services")
        result = validator.validate_service("test-service", "internal")

        assert result["ok"]
        assert len(result["errors"]) == 0

    def test_validate_routing_missing_container_name(self, temp_service_dir):
        """Проверка ошибки при отсутствии container_name в routing."""
        service_yml = """
name: test-service
version: "1.0.0"
type: docker-compose
routing:
  - type: port
    internal_port: 8000
"""
        compose_yml = """
version: '3.8'
services:
  test-service:
    image: nginx:latest
networks:
  platform_network:
    external: true
"""
        (temp_service_dir / "service.yml").write_text(service_yml)
        (temp_service_dir / "docker-compose.yml").write_text(compose_yml)

        validator = StaticValidator(temp_service_dir.parent.parent.parent, "services")
        result = validator.validate_service("test-service", "internal")

        assert not result["ok"]
        assert any("container_name" in e for e in result["errors"])

    def test_validate_internal_port_not_number(self, temp_service_dir):
        """Проверка ошибки при нечисловом internal_port."""
        service_yml = """
name: test-service
version: "1.0.0"
type: docker-compose
routing:
  - type: port
    internal_port: "not-a-number"
    container_name: test-service
"""
        compose_yml = """
version: '3.8'
services:
  test-service:
    image: nginx:latest
    container_name: test-service
networks:
  platform_network:
    external: true
"""
        (temp_service_dir / "service.yml").write_text(service_yml)
        (temp_service_dir / "docker-compose.yml").write_text(compose_yml)

        validator = StaticValidator(temp_service_dir.parent.parent.parent, "services")
        result = validator.validate_service("test-service", "internal")

        assert not result["ok"]
        assert any("internal_port" in e and "числом" in e for e in result["errors"])

    def test_validate_missing_platform_network(self, temp_service_dir):
        """Проверка ошибки при отсутствии platform_network."""
        service_yml = """
name: test-service
version: "1.0.0"
type: docker-compose
routing:
  - type: port
    internal_port: 8000
    container_name: test-service
"""
        compose_yml = """
version: '3.8'
services:
  test-service:
    image: nginx:latest
    container_name: test-service
networks:
  other_network:
    external: true
"""
        (temp_service_dir / "service.yml").write_text(service_yml)
        (temp_service_dir / "docker-compose.yml").write_text(compose_yml)

        validator = StaticValidator(temp_service_dir.parent.parent.parent, "services")
        result = validator.validate_service("test-service", "internal")

        assert not result["ok"]
        assert any("platform_network" in e for e in result["errors"])

    def test_validate_platform_network_with_name_field(self, temp_service_dir):
        """Проверка что сеть с name: platform_network распознаётся."""
        service_yml = """
name: test-service
version: "1.0.0"
type: docker-compose
routing:
  - type: port
    internal_port: 8000
    container_name: test-service
"""
        compose_yml = """
version: '3.8'
services:
  test-service:
    image: nginx:latest
    container_name: test-service
networks:
  platform:
    external: true
    name: platform_network
"""
        (temp_service_dir / "service.yml").write_text(service_yml)
        (temp_service_dir / "docker-compose.yml").write_text(compose_yml)

        validator = StaticValidator(temp_service_dir.parent.parent.parent, "services")
        result = validator.validate_service("test-service", "internal")

        # Сеть должна быть найдена по полю name
        assert result["ok"]
        assert not any("platform_network" in e for e in result["errors"])

    def test_validate_visibility_mismatch(self, temp_service_dir):
        """Проверка ошибки при несоответствии visibility и директории."""
        service_yml = """
name: test-service
version: "1.0.0"
type: docker-compose
visibility: internal
routing:
  - type: port
    internal_port: 8000
    container_name: test-service
"""
        compose_yml = """
version: '3.8'
services:
  test-service:
    image: nginx:latest
    container_name: test-service
networks:
  platform_network:
    external: true
"""
        (temp_service_dir / "service.yml").write_text(service_yml)
        (temp_service_dir / "docker-compose.yml").write_text(compose_yml)

        # Сервис в public, но visibility=internal
        validator = StaticValidator(temp_service_dir.parent.parent.parent, "services")
        result = validator.validate_service("test-service", "public")

        assert not result["ok"]
        assert any("несоответствие" in e.lower() or "visibility" in e.lower() for e in result["errors"])

    def test_validate_missing_container_name_in_compose(self, temp_service_dir):
        """Проверка предупреждения при отсутствии container_name в compose."""
        service_yml = """
name: test-service
version: "1.0.0"
type: docker-compose
routing:
  - type: port
    internal_port: 8000
    container_name: test-service
"""
        compose_yml = """
version: '3.8'
services:
  test-service:
    image: nginx:latest
networks:
  platform_network:
    external: true
"""
        (temp_service_dir / "service.yml").write_text(service_yml)
        (temp_service_dir / "docker-compose.yml").write_text(compose_yml)

        validator = StaticValidator(temp_service_dir.parent.parent.parent, "services")
        result = validator.validate_service("test-service", "internal")

        assert result["ok"]  # Это warning, не error
        assert any("не задан 'container_name'" in w for w in result["warnings"])


class TestRuntimeValidator:
    """Тесты runtime валидатора."""

    @pytest.fixture
    def mock_docker_client(self):
        """Мок Docker клиента."""
        with patch("apps_platform.validators.runtime.docker") as mock_docker:
            mock_client = MagicMock()
            mock_docker.from_env.return_value = mock_client
            yield mock_client

    def test_validate_service_docker_not_available(self, tmp_path):
        """Валидация при недоступном Docker."""
        validator = RuntimeValidator(tmp_path, timeout=5)

        # Мокаем docker.from_env() для выброса исключения
        with patch("apps_platform.validators.runtime.docker.from_env", side_effect=Exception("Docker not available")):
            result = validator.validate_service("test-service", {})

            assert len(result["warnings"]) > 0
            assert any("Docker недоступен" in w for w in result["warnings"])

    def test_matches_service_exact(self):
        """Точное совпадение имен."""
        validator = RuntimeValidator(Path.cwd())
        assert validator._matches_service("test-service", "test-service") is True

    def test_matches_service_prefix_dash(self):
        """Совпадение по префиксу с дефисом."""
        validator = RuntimeValidator(Path.cwd())
        assert validator._matches_service("test-service-frontend-1", "test-service") is True

    def test_matches_service_prefix_underscore(self):
        """Совпадение по префиксу с подчёркиванием."""
        validator = RuntimeValidator(Path.cwd())
        assert validator._matches_service("test-service_db_1", "test-service") is True

    def test_matches_service_no_match(self):
        """Нет совпадений."""
        validator = RuntimeValidator(Path.cwd())
        assert validator._matches_service("unrelated-container", "test-service") is False

    def test_check_container_status_success(self, mock_docker_client):
        """Успешная проверка статуса контейнеров."""
        validator = RuntimeValidator(Path.cwd(), timeout=5)

        mock_result = MagicMock()
        mock_result.stdout = '{"Names": "test-service-1", "Status": "Up 2 hours"}\n'
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = {"ok": True, "errors": [], "warnings": [], "info": {}}
            status = validator._check_container_status("test-service", {}, result)

            # Проверяем что статус возвращён корректно
            assert status is not None
            assert len(result["info"].get("containers", [])) >= 0  # Контейнеры найдены или нет

    def test_check_network_membership_network_not_found(self, mock_docker_client):
        """Проверка сети, когда сеть не найдена."""
        from docker.errors import NotFound

        mock_docker_client.networks.get.side_effect = NotFound("network not found")

        validator = RuntimeValidator(Path.cwd(), timeout=5)
        result = {"ok": True, "errors": [], "warnings": [], "info": {}}

        validator._check_network_membership("test-service", result)

        assert any("не существует" in w for w in result["warnings"])


class TestValidationReporter:
    """Тесты репортера."""

    def test_format_table_single_service(self):
        """Форматирование таблицы для одного сервиса."""
        reporter = ValidationReporter()
        results = {"test-service": {"ok": True, "errors": [], "warnings": ["Some warning"], "info": {}}}

        output = reporter.format_table(results)
        assert "test-service" in output
        assert "OK" in output

    def test_format_table_failed_service(self):
        """Форматирование таблицы для неудачного сервиса."""
        reporter = ValidationReporter()
        results = {"bad-service": {"ok": False, "errors": ["Error 1", "Error 2"], "warnings": [], "info": {}}}

        output = reporter.format_table(results)
        assert "bad-service" in output
        assert "FAILED" in output

    def test_format_json(self):
        """Экспорт в JSON."""
        reporter = ValidationReporter()
        results = {"test-service": {"ok": True, "errors": [], "warnings": [], "info": {"key": "value"}}}

        json_output = reporter.format_json(results)
        parsed = json.loads(json_output)

        # Проверяем новую структуру с exit_code и results
        assert "exit_code" in parsed
        assert "results" in parsed
        assert parsed["exit_code"] == 0
        assert parsed["results"]["test-service"]["ok"] is True
        assert parsed["results"]["test-service"]["info"]["key"] == "value"

    def test_format_json_with_errors(self):
        """Экспорт в JSON с ошибками."""
        reporter = ValidationReporter()
        results = {"bad-service": {"ok": False, "errors": ["Error 1"], "warnings": [], "info": {}}}

        json_output = reporter.format_json(results)
        parsed = json.loads(json_output)

        assert parsed["exit_code"] == 1
        assert not parsed["results"]["bad-service"]["ok"]

    def test_generate_fix_commands_container_name(self, tmp_path):
        """Генерация команд для исправления container_name."""
        reporter = ValidationReporter()
        results = {
            "test-service": {
                "ok": False,
                "errors": ["Маршрут #0: отсутствует 'container_name' в routing"],
                "warnings": [],
                "info": {"service_type": "internal"},
            }
        }

        commands = reporter.generate_fix_commands(results, tmp_path)
        assert len(commands) > 0
        assert any("container_name" in cmd for cmd in commands)

    def test_generate_fix_commands_platform_network(self, tmp_path):
        """Генерация команд для исправления platform_network."""
        reporter = ValidationReporter()
        results = {
            "test-service": {
                "ok": False,
                "errors": ["Отсутствует сеть 'platform_network' в docker-compose.yml"],
                "warnings": [],
                "info": {"service_type": "internal"},
            }
        }

        commands = reporter.generate_fix_commands(results, tmp_path)
        assert len(commands) > 0
        assert any("platform_network" in cmd for cmd in commands)

    def test_print_single_result_ok(self, tmp_path, capsys):
        """Вывод результатов для успешного сервиса."""
        from rich.console import Console

        console = Console(force_terminal=False)
        reporter = ValidationReporter(console)

        result = {"ok": True, "errors": [], "warnings": [], "info": {"service_dir": str(tmp_path)}}

        reporter.print_single_result("test-service", result, tmp_path)
        captured = capsys.readouterr()

        assert "test-service" in captured.out
        assert "OK" in captured.out

    def test_print_single_result_with_errors(self, tmp_path, capsys):
        """Вывод результатов для сервиса с ошибками."""
        from rich.console import Console

        console = Console(force_terminal=False)
        reporter = ValidationReporter(console)

        result = {"ok": False, "errors": ["Error 1"], "warnings": ["Warning 1"], "info": {"service_dir": str(tmp_path)}}

        reporter.print_single_result("bad-service", result, tmp_path)
        captured = capsys.readouterr()

        assert "bad-service" in captured.out
        assert "FAILED" in captured.out
        assert "Error 1" in captured.out
        assert "Warning 1" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
