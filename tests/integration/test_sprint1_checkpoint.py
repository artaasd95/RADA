from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.unit
def test_sprint1_foundation_artifacts_exist() -> None:
    required = [
        "pyproject.toml",
        "docker-compose.yml",
        "configs/dev.yaml",
        "src/rada/__init__.py",
        "src/rada/main.py",
        "src/rada/schemas.py",
    ]

    for path in required:
        assert Path(path).exists(), f"missing required artifact: {path}"
