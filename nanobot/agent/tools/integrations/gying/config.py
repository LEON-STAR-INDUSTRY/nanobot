"""Configuration for gying integration."""

from pydantic import BaseModel


class GyingConfig(BaseModel):
    """gying.org scraper configuration."""

    enabled: bool = False
    browser_data_dir: str = ""
    headless: bool = True
    check_schedule: str = "0 9 * * *"
