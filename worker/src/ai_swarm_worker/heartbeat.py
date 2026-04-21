from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from typing import Protocol

logger = logging.getLogger(__name__)


class Publishable(Protocol):
    def publish(self, topic: str, payload: str, retain: bool = False) -> None: ...


class HeartbeatConfig(Protocol):
    worker_id: str
    heartbeat_interval: int


class HeartbeatPublisher:
    def __init__(self, mqtt_client: Publishable, config: HeartbeatConfig) -> None:
        self.mqtt_client = mqtt_client
        self.config = config
        self._timer: threading.Timer | None = None
        self._stopped = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        self._stopped.clear()
        self._publish()

    def stop(self) -> None:
        self._stopped.set()
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _publish(self) -> None:
        if self._stopped.is_set():
            return

        heartbeat = {
            "worker_id": self.config.worker_id,
            "status": "idle",
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "version": "0.1.0",
        }
        self.mqtt_client.publish(
            f"workers/{self.config.worker_id}/heartbeat",
            json.dumps(heartbeat),
        )
        self.mqtt_client.publish(
            f"workers/{self.config.worker_id}/status",
            "idle",
            retain=True,
        )
        logger.debug("Published heartbeat", extra={"worker_id": self.config.worker_id})
        self._schedule_next()

    def _schedule_next(self) -> None:
        with self._lock:
            if self._stopped.is_set():
                return
            self._timer = threading.Timer(self.config.heartbeat_interval, self._publish)
            self._timer.daemon = True
            self._timer.start()
