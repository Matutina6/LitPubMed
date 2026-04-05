from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


def _resolve_llm_api_key() -> str:
    """百炼 / DashScope OpenAI 兼容接口常用密钥环境变量（优先级从左到右）。"""
    for name in (
        "LITPUBMED_LLM_API_KEY",
        "DASHSCOPE_API_KEY",
        "BAILIAN_API_KEY",
    ):
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LITPUBMED_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    config_dir: Path = Field(default_factory=lambda: Path.home() / ".litpubmed")
    # 百炼「OpenAI 兼容」下的模型 id，可用环境变量 LITPUBMED_LLM_MODEL 覆盖
    llm_model: str = "qwen-max"
    # 北京地域 OpenAI 兼容模式；新加坡等可改为 dashscope-intl / cn-hongkong 等地址
    llm_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str = Field(default_factory=_resolve_llm_api_key)
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    api_token: str = Field(default="", description="Optional Bearer token for HTTP API")

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.json"

    @property
    def db_file(self) -> Path:
        return self.config_dir / "litpubmed.db"

    @property
    def pdf_dir(self) -> Path:
        return self.config_dir / "pdfs"

    def load_json_overrides(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.is_file():
            return
        data: dict[str, Any] = json.loads(self.config_file.read_text(encoding="utf-8"))
        if "llm_model" in data:
            self.llm_model = str(data["llm_model"])
        if "llm_api_base" in data:
            self.llm_api_base = str(data["llm_api_base"])

    def save_json(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        payload = {"llm_model": self.llm_model, "llm_api_base": self.llm_api_base}
        self.config_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
