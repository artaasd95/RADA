"""Pipeline configuration loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class DatasourceConfig(BaseModel):
    id: str
    type: str
    uri: str | None = None
    contract: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class PreprocessingConfig(BaseModel):
    stages: list[dict[str, Any]] = Field(default_factory=list)


class SinkConfig(BaseModel):
    type: str
    contract: str | None = None
    uri: str | None = None
    format: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    version: int = 1
    mode: Literal["usage", "export"]
    datasources: list[DatasourceConfig] = Field(default_factory=list)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    sinks: dict[str, SinkConfig | dict[str, Any]] = Field(default_factory=dict)


def _expand_env(value: str) -> str:
    return os.path.expandvars(value)


def _expand_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return _expand_env(obj)
    if isinstance(obj, dict):
        return {key: _expand_obj(item) for key, item in obj.items()}
    if isinstance(obj, list):
        return [_expand_obj(item) for item in obj]
    return obj


def load_pipeline_config(path: str | Path) -> PipelineConfig:
    """Load and validate a pipeline YAML file."""
    raw_path = Path(path)
    data = yaml.safe_load(raw_path.read_text(encoding="utf-8"))
    expanded = _expand_obj(data)
    return PipelineConfig.model_validate(expanded)
