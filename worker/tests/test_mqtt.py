from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_swarm_worker.config import WorkerConfig
from ai_swarm_worker.mqtt import _TASK_TOPIC, MQTTClient


@pytest.fixture()
def config(monkeypatch: pytest.MonkeyPatch) -> WorkerConfig:
    monkeypatch.setenv("AI_SWARM_MQTT_BROKER_URL", "mqtts://broker.example.com:8883")
    monkeypatch.setenv("AI_SWARM_MQTT_USERNAME", "user")
    monkeypatch.setenv("AI_SWARM_MQTT_PASSWORD", "pass")
    return WorkerConfig()


def test_resubscribes_on_reconnect(config: WorkerConfig) -> None:
    with patch("paho.mqtt.client.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.is_connected.return_value = False

        client = MQTTClient(config)
        client.subscribe_tasks(lambda _: None)

        # Simulate reconnect: _on_connect called with reason_code 0
        mock_reason = MagicMock()
        mock_reason.__eq__ = lambda self, other: other == 0  # type: ignore[method-assign]
        client._on_connect(mock_client, None, MagicMock(), mock_reason, None)

        mock_client.subscribe.assert_called_once_with(_TASK_TOPIC, qos=1)


def test_no_subscribe_without_callback(config: WorkerConfig) -> None:
    with patch("paho.mqtt.client.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        client = MQTTClient(config)
        # No subscribe_tasks called → callback is None

        mock_reason = MagicMock()
        mock_reason.__eq__ = lambda self, other: other == 0  # type: ignore[method-assign]
        client._on_connect(mock_client, None, MagicMock(), mock_reason, None)

        mock_client.subscribe.assert_not_called()
