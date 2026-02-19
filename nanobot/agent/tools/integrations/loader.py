"""IntegrationLoader: discover and register integration tools from subdirectories."""

import importlib
from pathlib import Path
from typing import Any

from loguru import logger

# Directory containing integration subdirectories (cloud115/, gying/, etc.)
_INTEGRATIONS_DIR = Path(__file__).parent


class IntegrationLoader:
    """Scans integrations/ subdirectories and registers enabled tools.

    Each integration subdirectory must contain:
      - config.py  with a Pydantic BaseModel (discovered automatically)
      - tool.py    with a module-level TOOLS list descriptor

    TOOLS descriptor format::

        TOOLS = [
            {
                "class": SomeToolClass,       # Tool subclass
                "config_map": {               # config field → constructor kwarg
                    "session_path": "session_path",
                },
                "workspace_fields": {         # (optional) kwarg → workspace-relative path
                    "seen_file": "film_download/seen_movies.json",
                },
            },
        ]
    """

    def __init__(self, workspace: Path | None = None):
        self._workspace = workspace

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_all(self, registry: Any, integrations_config: Any) -> list[str]:
        """Discover integrations and register enabled tools.

        Args:
            registry: ToolRegistry instance with a ``register(tool)`` method.
            integrations_config: Either an ``IntegrationsConfig`` Pydantic model
                or a raw ``dict[str, dict]`` keyed by integration name.

        Returns:
            List of registered tool names.
        """
        if integrations_config is None:
            return []

        registered: list[str] = []
        for name in self._discover_integrations():
            try:
                tools = self._load_integration(name, integrations_config, registry)
                registered.extend(tools)
            except Exception as e:
                logger.warning(f"Integration '{name}' failed to load: {e}")
        return registered

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover_integrations(self) -> list[str]:
        """Return sorted list of integration directory names that contain tool.py."""
        names = []
        for child in sorted(_INTEGRATIONS_DIR.iterdir()):
            if child.is_dir() and (child / "tool.py").exists():
                names.append(child.name)
        return names

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_integration(
        self,
        name: str,
        integrations_config: Any,
        registry: Any,
    ) -> list[str]:
        """Load a single integration and register its tools.

        Returns list of registered tool names.
        """
        # 1. Extract config dict for this integration
        cfg_dict = self._get_config_dict(name, integrations_config)
        if cfg_dict is None:
            return []

        # 2. Check enabled flag
        if not cfg_dict.get("enabled", False):
            logger.debug(f"Integration '{name}' is disabled, skipping.")
            return []

        # 3. Import config.py and validate
        config_mod = importlib.import_module(
            f"nanobot.agent.tools.integrations.{name}.config"
        )
        # Find the first BaseModel subclass in the module
        config_cls = None
        for attr_name in dir(config_mod):
            obj = getattr(config_mod, attr_name)
            if (
                isinstance(obj, type)
                and hasattr(obj, "model_validate")
                and attr_name != "BaseModel"
            ):
                config_cls = obj
                break

        if config_cls is None:
            logger.warning(f"No config model found in integrations/{name}/config.py")
            return []

        validated_cfg = config_cls.model_validate(cfg_dict)

        # 4. Import tool.py and read TOOLS descriptor
        tool_mod = importlib.import_module(
            f"nanobot.agent.tools.integrations.{name}.tool"
        )
        tools_desc = getattr(tool_mod, "TOOLS", None)
        if not tools_desc:
            logger.warning(f"No TOOLS descriptor in integrations/{name}/tool.py")
            return []

        # 5. Instantiate and register each tool
        registered: list[str] = []
        for desc in tools_desc:
            tool_cls = desc["class"]
            config_map = desc.get("config_map", {})
            workspace_fields = desc.get("workspace_fields", {})

            kwargs = {}
            # Map config fields to constructor kwargs
            for cfg_field, kwarg_name in config_map.items():
                if hasattr(validated_cfg, cfg_field):
                    kwargs[kwarg_name] = getattr(validated_cfg, cfg_field)

            # Map workspace-relative paths
            for kwarg_name, rel_path in workspace_fields.items():
                if self._workspace:
                    kwargs[kwarg_name] = str(self._workspace / rel_path)

            tool_instance = tool_cls(**kwargs)
            registry.register(tool_instance)
            registered.append(tool_instance.name)
            logger.info(f"Registered integration tool: {tool_instance.name}")

        return registered

    # ------------------------------------------------------------------
    # Config extraction
    # ------------------------------------------------------------------

    def _get_config_dict(self, name: str, integrations_config: Any) -> dict | None:
        """Extract config dict for a named integration.

        Supports both Pydantic models (via attribute access + model_dump)
        and raw dicts.
        """
        if isinstance(integrations_config, dict):
            return integrations_config.get(name)

        # Pydantic model: try attribute access
        if hasattr(integrations_config, name):
            attr = getattr(integrations_config, name)
            if hasattr(attr, "model_dump"):
                return attr.model_dump()
            if isinstance(attr, dict):
                return attr
            return None

        return None
