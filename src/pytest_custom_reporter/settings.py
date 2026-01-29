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
    
    # Report generation settings
    generate_report: bool = Field(default=False, description="Generate custom report by default")
    report_file: str | None = Field(default=None, description="Default output file for custom report")
    report_url: str | None = Field(default=None, description="Default remote server URL to send reports")
    report_format: str = Field(default="json", description="Default report format (json or yaml)")


def get_settings() -> PluginSettings:
    return PluginSettings()
