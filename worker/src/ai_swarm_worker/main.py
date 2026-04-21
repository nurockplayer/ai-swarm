from __future__ import annotations

import json
import logging
import signal
import sys
import threading
from datetime import UTC, datetime

import click

from ai_swarm_worker.config import WorkerConfig
from ai_swarm_worker.executor import TaskExecutor
from ai_swarm_worker.heartbeat import HeartbeatPublisher
from ai_swarm_worker.mqtt import MQTTClient


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        return json.dumps(payload)


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)


@click.group()
def cli() -> None:
    pass


@cli.command()
def start() -> None:
    """Start the worker daemon."""
    config = WorkerConfig()
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)
    stop_event = threading.Event()
    mqtt_client = MQTTClient(config)
    heartbeat = HeartbeatPublisher(mqtt_client, config)
    executor = TaskExecutor(mqtt_client, config)

    def request_stop(signum: int, frame: object | None) -> None:
        del frame
        logger.info("Received shutdown signal", extra={"signal": signum})
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    try:
        mqtt_client.connect()
        heartbeat.start()
        mqtt_client.subscribe_tasks(executor.handle_message)
        stop_event.wait()
    finally:
        heartbeat.stop()
        mqtt_client.disconnect()


@cli.command()
def stop() -> None:
    """Stop the worker daemon."""
    click.echo("stop is not implemented yet")


@cli.command()
def status() -> None:
    """Show worker daemon status."""
    click.echo("status is not implemented yet")
