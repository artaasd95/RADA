"""Import smoke tests for core package modules."""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import rada


@pytest.mark.unit
def test_rada_package_imports() -> None:
    assert rada.__name__ == "rada"


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_name",
    [
        "rada.main",
        "rada.schemas",
        "rada.core.decision_loop",
        "rada.core.reflection_loop",
        "rada.core.search_loop",
        "rada.calc.engine",
        "rada.audit.api",
        "rada.feedback.api",
        "rada.models.registry",
        "rada.models.resolver",
        "rada.llm_integration.factory",
        "rada.training.config",
    ],
)
def test_import_core_modules(module_name: str) -> None:
    importlib.import_module(module_name)


@pytest.mark.unit
def test_import_all_rada_submodules() -> None:
    """Every discoverable rada submodule should import without error."""
    prefix = f"{rada.__name__}."
    for module_info in pkgutil.walk_packages(rada.__path__, prefix):
        if module_info.name.endswith(".adapters._http_base"):
            continue
        importlib.import_module(module_info.name)
