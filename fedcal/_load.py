import importlib.util
from types import ModuleType
from typing import Any, Self, Tuple


class LazyModule:
    _cache: dict[str, Self] = {}

    def __new__(cls, name: str, package: str | None = None) -> Self:
        key: tuple[str, str | None] = (name, package)
        if key not in cls._cache:
            cls._cache[key] = super().__new__(cls)
        return cls._cache[key]

    def __init__(self, name: str, package: str | None = None) -> None:
        if not hasattr(self, "_initialized"):
            self._name: str = name
            self._package: str | None = package
            self._module: LazyModule | None = None
            self._loaded: bool = False
            self._initialized: bool = True

    def __getattr__(self, item) -> Any:
        if self._module is None:
            self._module: ModuleType = importlib.import_module(
                name=self._name, package=self._package
            )
            self._loaded = True
        return getattr(self._module, item)


class LoadOrchestrator:
    _instance: Self | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance: Self = super().__new__(cls)
            cls._instance._registered_modules: set = set()
            cls._instance._modules: dict = {}
        return cls._instance

    def register(self, module_name: str, package_name: str | None = None) -> None:
        self._registered_modules.add((module_name, package_name))

    def __getattr__(self, name: str) -> Any:
        package = next(
            (pkg for mod, pkg in self._registered_modules if mod == name), None
        )
        key: tuple[str, ModuleType | None] = (name, package)

        if key not in self._modules and key in self._registered_modules:
            self._modules[key] = LazyModule(name=name, package=package)
        return self._modules.get(key, None)

    @property
    def registered(self) -> list[Tuple[str, str | None]]:
        return list(self._registered_modules)

    @property
    def loaded(self) -> list[Tuple[str, str | None]]:
        return [name for name, module in self._modules.items() if module._loaded]
