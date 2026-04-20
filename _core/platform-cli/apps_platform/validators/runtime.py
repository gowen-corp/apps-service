"""
Runtime validation of service containers and health checks.
"""

import json
import subprocess
from pathlib import Path

import docker
from docker.errors import DockerException, NotFound


class PlatformValidationError(Exception):
    """Кастомное исключение для ошибок валидации."""

    pass


class RuntimeValidator:
    """Валидатор runtime-состояния сервисов."""

    def __init__(self, project_root: Path, timeout: int = 5) -> None:
        self.project_root = project_root
        self.timeout = timeout

    def validate_service(self, service_name: str, compose_config: dict) -> dict:
        """
        Валидация runtime-состояния сервиса.

        Returns:
            dict с результатами: {ok: bool, errors: list, warnings: list, info: dict}
        """
        result = {"ok": True, "errors": [], "warnings": [], "info": {}}

        # Проверяем доступность Docker перед выполнением проверок
        try:
            import docker as docker_module

            _ = docker_module.from_env()
        except Exception:
            result["warnings"].append("Docker недоступен: runtime-проверки пропущены")
            return result

        # Проверяем статус контейнеров
        self._check_container_status(service_name, compose_config, result)

        # Проверяем принадлежность к platform_network
        self._check_network_membership(service_name, result)

        # Проверяем health endpoint (если задан)
        self._check_health_endpoint(service_name, compose_config, result)

        return result

    def _check_container_status(self, service_name: str, compose_config: dict, result: dict) -> dict:
        """Проверка статуса контейнеров сервиса."""
        try:
            # Получаем список всех контейнеров через JSON формат
            proc = subprocess.run(
                ["docker", "ps", "-a", "--format", "json"], capture_output=True, text=True, check=True, timeout=10
            )

            containers = []
            for line in proc.stdout.strip().splitlines():
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    name = entry.get("Names", "")
                    status = entry.get("Status", "")

                    # Проверяем, относится ли контейнер к сервису
                    if self._matches_service(name, service_name):
                        containers.append({"name": name, "status": status})
                except json.JSONDecodeError:
                    continue

            if not containers:
                result["warnings"].append(f"Контейнеры для сервиса '{service_name}' не найдены")
                result["info"]["containers"] = []
                return {"running": False, "containers": []}

            result["info"]["containers"] = containers

            # Проверяем, запущены ли контейнеры
            running_count = sum(1 for c in containers if "running" in c["status"].lower())

            if running_count == 0:
                result["warnings"].append(f"Ни один контейнер сервиса '{service_name}' не запущен")
                return {"running": False, "containers": containers}

            return {"running": True, "containers": containers}

        except subprocess.CalledProcessError as e:
            result["errors"].append(f"Ошибка получения статуса контейнеров: {e}")
            return {"running": False, "containers": []}
        except FileNotFoundError:
            result["warnings"].append("Docker не доступен")
            return {"running": False, "containers": []}
        except subprocess.TimeoutExpired:
            result["warnings"].append("Таймаут при получении статуса контейнеров")
            return {"running": False, "containers": []}

    def _matches_service(self, container_name: str, service_name: str) -> bool:
        """Гибкое сопоставление имени контейнера и сервиса."""
        if container_name == service_name:
            return True
        if container_name.startswith(f"{service_name}-") or container_name.startswith(f"{service_name}_"):
            return True
        if container_name.endswith(f"-{service_name}") or container_name.endswith(f"_{service_name}"):
            return True
        if service_name in container_name:
            return True
        return False

    def _check_network_membership(self, service_name: str, result: dict) -> None:
        """Проверка принадлежности контейнеров к platform_network."""
        try:
            client = docker.from_env()

            # Получаем сеть platform_network
            try:
                network = client.networks.get("platform_network")
            except NotFound:
                result["warnings"].append("Сеть 'platform_network' не существует")
                client.close()
                return

            network_containers = set()
            for container in network.containers:
                network_containers.add(container.name)

            # Проверяем, есть ли контейнеры сервиса в сети
            service_containers_in_network = [
                name for name in network_containers if self._matches_service(name, service_name)
            ]

            if not service_containers_in_network:
                # Проверяем, есть ли вообще контейнеры сервиса
                all_containers = client.containers.list(all=True)
                service_containers = [c.name for c in all_containers if self._matches_service(c.name, service_name)]

                if service_containers:
                    result["errors"].append(
                        f"Контейнеры сервиса '{service_name}' ({service_containers}) не подключены к 'platform_network'"
                    )

            result["info"]["network_containers"] = list(network_containers)
            client.close()

        except DockerException as e:
            result["warnings"].append(f"Ошибка проверки сети: {e}")
        except Exception as e:
            result["warnings"].append(f"Неожиданная ошибка проверки сети: {type(e).__name__}: {e}")

    def _check_health_endpoint(self, service_name: str, compose_config: dict, result: dict) -> None:
        """
        Проверка health endpoint через docker run --network platform_network.
        Использует alpine/curl с graceful fallback.
        """
        services = compose_config.get("services", {})
        if not services:
            return

        # Пытаемся получить health config из service.yml (передаётся через compose_config)
        # В реальном использовании health config передаётся отдельно
        health_config = result.get("health_config", {})

        if not health_config.get("enabled", False):
            return

        endpoint = health_config.get("endpoint", "/health")
        internal_port = health_config.get("internal_port", 80)

        # Получаем имя контейнера
        container_name = None
        for _svc_name, svc_config in services.items():
            if "container_name" in svc_config:
                container_name = svc_config["container_name"]
                break

        if not container_name:
            container_name = service_name

        # Проверяем, запущен ли контейнер
        try:
            client = docker.from_env()
            container = client.containers.get(container_name)

            if container.status != "running":
                result["warnings"].append(f"Контейнер '{container_name}' не запущен, health check пропущен")
                client.close()
                return

            client.close()
        except NotFound:
            result["warnings"].append(f"Контейнер '{container_name}' не найден")
            return
        except Exception:
            result["warnings"].append("Docker недоступен для health check")
            return

        # Выполняем health check через docker run
        base_url = f"http://{container_name}:{internal_port}"
        health_url = f"{base_url}{endpoint}"

        try:
            # Пробуем использовать curl в alpine
            cmd = [
                "docker",
                "run",
                "--rm",
                "--network",
                "platform_network",
                "curlimages/curl:latest",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "--connect-timeout",
                str(self.timeout),
                "--max-time",
                str(self.timeout),
                health_url,
            ]

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 2)

            if proc.returncode == 0:
                http_code = proc.stdout.strip()
                if http_code.isdigit() and 200 <= int(http_code) < 400:
                    result["info"]["health_status"] = f"OK ({http_code})"
                else:
                    result["warnings"].append(f"Health endpoint вернул HTTP {http_code}")
            else:
                result["warnings"].append(f"Health check failed: {proc.stderr.strip()[:100]}")

        except subprocess.TimeoutExpired:
            result["warnings"].append(f"Таймаут health check ({self.timeout}s)")
        except FileNotFoundError:
            result["warnings"].append("Docker не доступен для health check")
        except Exception as e:
            result["warnings"].append(f"Health check error: {type(e).__name__}: {e}")
