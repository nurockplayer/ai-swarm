from __future__ import annotations

from ai_swarm_worker.config import WorkerConfig


def test_worker_id_defaults_to_hostname_pid(monkeypatch) -> None:
    monkeypatch.setenv("AI_SWARM_MQTT_BROKER_URL", "mqtts://mqtt.example.com:8883")
    monkeypatch.setenv("AI_SWARM_MQTT_USERNAME", "worker")
    monkeypatch.setenv("AI_SWARM_MQTT_PASSWORD", "secret")

    config = WorkerConfig()

    assert "-" in config.worker_id


def test_custom_worker_id(monkeypatch) -> None:
    monkeypatch.setenv("AI_SWARM_WORKER_ID", "my-custom-worker")
    monkeypatch.setenv("AI_SWARM_MQTT_BROKER_URL", "mqtts://mqtt.example.com:8883")
    monkeypatch.setenv("AI_SWARM_MQTT_USERNAME", "worker")
    monkeypatch.setenv("AI_SWARM_MQTT_PASSWORD", "secret")

    config = WorkerConfig()

    assert config.worker_id == "my-custom-worker"
