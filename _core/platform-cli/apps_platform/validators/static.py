"""
Static validation of service manifests (service.yml, docker-compose.yml).
"""

from pathlib import Path

import yaml


class PlatformValidationError(Exception):
    """Кастомное исключение для ошибок валидации."""

    pass


class StaticValidator:
    """Валидатор статических конфигураций сервисов."""

    def __init__(self, project_root: Path, services_path: str = "services") -> None:
        self.project_root = project_root
        self.services_path = project_root / services_path

    def validate_service(self, service_name: str, service_type: str) -> dict:
        """
        Валидация сервиса: парсинг YAML, проверка routing, compose-сетей.

        Returns:
            dict с результатами валидации: {ok: bool, errors: list, warnings: list, info: dict}
        """
        result = {"ok": True, "errors": [], "warnings": [], "info": {}}

        # Определяем путь к сервису
        if service_type == "core":
            service_dir = self.project_root / "_core" / service_name
        else:
            service_dir = self.services_path / service_type / service_name

        service_yml = service_dir / "service.yml"
        compose_yml = service_dir / "docker-compose.yml"

        # Проверяем существование файлов
        if not service_yml.exists():
            if service_type == "core":
                # Core-сервисы могут не иметь service.yml (инфраструктура)
                msg = f"Core-сервис '{service_name}': service.yml отсутствует"
                result["warnings"].append(msg)
                # Продолжаем проверку docker-compose.yml если есть
                if not compose_yml.exists():
                    msg2 = f"Core-сервис '{service_name}': docker-compose.yml отсутствует"
                    result["warnings"].append(msg2)
                    return result
            else:
                result["ok"] = False
                result["errors"].append(f"Файл service.yml не найден: {service_yml}")
                return result

        if not compose_yml.exists():
            result["ok"] = False
            result["errors"].append(f"Файл docker-compose.yml не найден: {compose_yml}")
            return result

        # Парсим YAML
        try:
            with open(service_yml) as f:
                service_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            result["ok"] = False
            result["errors"].append(f"Ошибка парсинга service.yml: {e}")
            return result

        try:
            with open(compose_yml) as f:
                compose_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            result["ok"] = False
            result["errors"].append(f"Ошибка парсинга docker-compose.yml: {e}")
            return result

        result["info"]["service_config"] = service_config
        result["info"]["compose_config"] = compose_config
        result["info"]["service_dir"] = str(service_dir)

        # Валидация service.yml
        self._validate_service_yml(service_config, service_name, service_type, result)

        # Валидация docker-compose.yml
        self._validate_compose_yml(compose_config, service_config, service_name, result)

        # Проверка соответствия visibility и директории
        self._check_visibility_match(service_config, service_type, result)

        return result

    def _validate_service_yml(self, config: dict, service_name: str, service_type: str, result: dict) -> None:
        """Валидация service.yml."""
        # Проверка обязательных полей
        required_fields = ["name", "version", "type"]
        for field in required_fields:
            if field not in config:
                result["warnings"].append(f"Отсутствует поле '{field}' в service.yml")

        # Валидация routing
        routing_configs = config.get("routing", [])
        if not routing_configs:
            result["warnings"].append("Не заданы маршруты (routing) в service.yml")
        else:
            for idx, route in enumerate(routing_configs):
                self._validate_route(route, idx, result)

    def _validate_route(self, route: dict, idx: int, result: dict) -> None:
        """Валидация отдельного маршрута."""
        # Проверка container_name
        if "container_name" not in route:
            result["errors"].append(f"Маршрут #{idx}: отсутствует 'container_name' в routing")
            result["ok"] = False

        # Проверка internal_port
        internal_port = route.get("internal_port")
        if internal_port is None:
            result["warnings"].append(f"Маршрут #{idx}: не указан 'internal_port', будет использован порт по умолчанию")
        else:
            if not isinstance(internal_port, int):
                try:
                    internal_port = int(internal_port)
                except (ValueError, TypeError):
                    result["errors"].append(
                        f"Маршрут #{idx}: 'internal_port' должен быть числом, получено: {internal_port}"
                    )
                    result["ok"] = False
            elif internal_port < 1 or internal_port > 65535:
                result["errors"].append(
                    f"Маршрут #{idx}: 'internal_port' должен быть в диапазоне 1-65535, получено: {internal_port}"
                )
                result["ok"] = False

    def _validate_compose_yml(
        self, compose_config: dict, service_config: dict, service_name: str, result: dict
    ) -> None:
        """Валидация docker-compose.yml."""
        services = compose_config.get("services", {})

        if not services:
            result["errors"].append("docker-compose.yml не содержит секции 'services'")
            return

        # Получаем ожидаемый container_name из service.yml
        expected_container_names = set()
        routing_configs = service_config.get("routing", [])
        for route in routing_configs:
            if "container_name" in route:
                expected_container_names.add(route["container_name"])

        # Также проверяем имя сервиса в самом top-level
        if service_config.get("name"):
            expected_container_names.add(service_config["name"])

        # Валидация каждого сервиса в compose
        for svc_name, svc_config in services.items():
            self._validate_compose_service(svc_name, svc_config, expected_container_names, result)

        # Проверка наличия platform_network
        networks = compose_config.get("networks", {})
        has_platform_net = any(
            net_name == "platform_network" or (isinstance(net_cfg, dict) and net_cfg.get("name") == "platform_network")
            for net_name, net_cfg in networks.items()
        )
        if not has_platform_net:
            result["errors"].append("Отсутствует сеть 'platform_network' в docker-compose.yml")
            result["ok"] = False
        else:
            # Находим конфигурацию platform_network для проверки external
            platform_net_config = None
            for net_name, net_cfg in networks.items():
                is_match = net_name == "platform_network" or (
                    isinstance(net_cfg, dict) and net_cfg.get("name") == "platform_network"
                )
                if is_match:
                    platform_net_config = net_cfg
                    break
            if platform_net_config and isinstance(platform_net_config, dict):
                if not platform_net_config.get("external"):
                    result["warnings"].append("Сеть 'platform_network' должна быть external: true")

    def _validate_compose_service(
        self, svc_name: str, svc_config: dict, expected_container_names: set, result: dict
    ) -> None:
        """Валидация отдельного сервиса в docker-compose.yml."""
        # Проверка container_name
        container_name = svc_config.get("container_name")

        if not container_name:
            # Если container_name не задан явно, Docker Compose использует формат {project}-{service}-1
            result["warnings"].append(
                f"Сервис '{svc_name}': не задан 'container_name'. "
                f"Docker Compose присвоит имя вида '{{project}}-{svc_name}-1'"
            )
        elif expected_container_names and container_name not in expected_container_names:
            # container_name есть, но не совпадает с ожидаемым из service.yml
            result["warnings"].append(
                f"Сервис '{svc_name}': 'container_name' ({container_name}) не совпадает с "
                f"ожидаемым из service.yml ({expected_container_names})"
            )

        # Проверка ports - internal_port должен соответствовать порту контейнера
        ports = svc_config.get("ports", [])
        routing_configs = result["info"].get("service_config", {}).get("routing", [])

        for route in routing_configs:
            internal_port = route.get("internal_port")
            if internal_port is not None:
                # Проверяем, есть ли такой порт в mapping
                port_found = False
                for port_mapping in ports:
                    if isinstance(port_mapping, str):
                        parts = port_mapping.split(":")
                        if len(parts) >= 2:
                            container_port = parts[-1].split("/")[0]  # убираем /tcp если есть
                            if container_port == str(internal_port):
                                port_found = True
                                break
                    elif isinstance(port_mapping, int):
                        if port_mapping == internal_port:
                            port_found = True
                            break

                if not port_found and ports:
                    result["warnings"].append(
                        f"Сервис '{svc_name}': declared internal_port {internal_port} не найден "
                        f"в портах контейнера {[str(p) for p in ports]}"
                    )

    def _check_visibility_match(self, service_config: dict, service_type: str, result: dict) -> None:
        """Проверка соответствия visibility и типа директории."""
        visibility = service_config.get("visibility", "")

        if service_type == "public" and visibility == "internal":
            result["errors"].append("Несоответствие: visibility='internal', но сервис находится в директории 'public'")
        elif service_type == "internal" and visibility == "public":
            result["errors"].append("Несоответствие: visibility='public', но сервис находится в директории 'internal'")
