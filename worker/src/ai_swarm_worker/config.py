from __future__ import annotations

import os
import socket

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_SWARM_", case_sensitive=False)

    worker_id: str = f"{socket.gethostname()}-{os.getpid()}"
    mqtt_broker_url: str
    mqtt_username: str
    mqtt_password: str
    mqtt_keepalive: int = 60
    heartbeat_interval: int = 30
    log_level: str = "INFO"
