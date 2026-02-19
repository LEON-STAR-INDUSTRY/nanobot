"""Configuration for cloud115 integration."""

from pydantic import BaseModel


class Cloud115Config(BaseModel):
    """115.com cloud storage configuration."""

    enabled: bool = False
    session_path: str = ""  # Default: ~/.nanobot/cloud115_session.json
    default_save_path: str = "/"  # Default 115 folder for downloads
