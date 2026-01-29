from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class PluginSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PYTEST_CUSTOM_REPORTER__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    name: str = Field(default="Custom Reporter", description="Name of the plugin")
    version: str = Field(default="1.0.0", description="Version of the plugin")


def get_settings() -> PluginSettings:
    return PluginSettings()
