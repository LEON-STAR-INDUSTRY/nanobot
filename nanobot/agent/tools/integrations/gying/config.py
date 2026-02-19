"""Configuration for gying integration."""

from pydantic import BaseModel


class GyingConfig(BaseModel):
    """gying.org scraper configuration."""

    enabled: bool = False
    browser_data_dir: str = ""  # Default: ~/.nanobot/browser_data/gying/
    headless: bool = True
    check_schedule: str = "0 9 * * *"
    notify_channel: str = "feishu"
    notify_to: str = ""
