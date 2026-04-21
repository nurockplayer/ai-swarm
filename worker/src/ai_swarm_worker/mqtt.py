from __future__ import annotations

import logging
import ssl
from collections.abc import Callable
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from ai_swarm_worker.config import WorkerConfig

logger = logging.getLogger(__name__)

_TASK_TOPIC = "$share/impl-workers/tasks/impl/+"


class MQTTClient:
    def __init__(self, config: WorkerConfig) -> None:
        self.config = config
        self._on_message_callback: Callable[[str], None] | None = None
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=config.worker_id,
            clean_session=True,
        )
        self.client.username_pw_set(config.mqtt_username, config.mqtt_password)
        self.client.will_set(
            f"workers/{config.worker_id}/status",
            payload="offline",
            qos=1,
            retain=True,
        )
        self.client.on_connect = self._on_connect

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del userdata, flags, properties
        if reason_code == 0:
            logger.info(
                "Connected to MQTT broker",
                extra={"worker_id": self.config.worker_id},
            )
            if self._on_message_callback is not None:
                client.subscribe(_TASK_TOPIC, qos=1)
        else:
            logger.error(
                "MQTT connection refused",
                extra={"reason_code": str(reason_code)},
            )

    def connect(self) -> None:
        parsed_url = urlparse(self.config.mqtt_broker_url)
        if (
            parsed_url.scheme != "mqtts"
            or not parsed_url.hostname
            or parsed_url.port is None
        ):
            msg = "mqtt_broker_url must use mqtts://host:port"
            raise ValueError(msg)

        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        tls_context.load_default_certs()
        self.client.tls_set_context(tls_context)
        logger.info(
            "Connecting to MQTT broker",
            extra={"host": parsed_url.hostname, "port": parsed_url.port},
        )
        self.client.connect_async(
            parsed_url.hostname,
            parsed_url.port,
            self.config.mqtt_keepalive,
        )
        self.client.loop_start()

    def subscribe_tasks(self, on_message: Callable[[str], None]) -> None:
        def handle_message(
            client: mqtt.Client,
            userdata: object,
            message: mqtt.MQTTMessage,
        ) -> None:
            del client, userdata
            on_message(message.payload.decode("utf-8"))

        self.client.on_message = handle_message
        self._on_message_callback = on_message
        if self.client.is_connected():
            self.client.subscribe(_TASK_TOPIC, qos=1)

    def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        self.client.publish(topic, payload=payload, qos=1, retain=retain)

    def disconnect(self) -> None:
        self.publish(f"workers/{self.config.worker_id}/status", "offline", retain=True)
        self.client.loop_stop()
        self.client.disconnect()
