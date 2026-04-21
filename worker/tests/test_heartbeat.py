from __future__ import annotations

from unittest.mock import Mock

import ai_swarm_worker.heartbeat as heartbeat_module
from ai_swarm_worker.heartbeat import HeartbeatPublisher


class FakeTimer:
    def __init__(self, interval: int, function) -> None:
        self.interval = interval
        self.function = function
        self.daemon = False
        self.cancelled = False

    def start(self) -> None:
        pass

    def cancel(self) -> None:
        self.cancelled = True


def test_start_publishes_heartbeat_and_status() -> None:
    mqtt_client = Mock()
    config = Mock(worker_id="worker-1", heartbeat_interval=60)
    publisher = HeartbeatPublisher(mqtt_client, config)

    publisher.start()
    publisher.stop()

    mqtt_client.publish.assert_any_call(
        "workers/worker-1/heartbeat",
        mqtt_client.publish.call_args_list[0].args[1],
    )
    mqtt_client.publish.assert_any_call("workers/worker-1/status", "idle", retain=True)


def test_stop_cancels_timer_and_stops_further_publishing(monkeypatch) -> None:
    timers: list[FakeTimer] = []

    def create_timer(interval: int, function) -> FakeTimer:
        timer = FakeTimer(interval, function)
        timers.append(timer)
        return timer

    monkeypatch.setattr(heartbeat_module.threading, "Timer", create_timer)
    mqtt_client = Mock()
    config = Mock(worker_id="worker-1", heartbeat_interval=60)
    publisher = HeartbeatPublisher(mqtt_client, config)

    publisher.start()
    publisher.stop()
    publish_count = mqtt_client.publish.call_count
    timers[0].function()

    assert timers[0].cancelled is True
    assert mqtt_client.publish.call_count == publish_count
