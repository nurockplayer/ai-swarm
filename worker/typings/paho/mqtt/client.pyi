from __future__ import annotations

import ssl
from typing import Any

class CallbackAPIVersion:
    VERSION2: CallbackAPIVersion


class MQTTMessage:
    payload: bytes


class Client:
    on_message: Any

    def __init__(
        self,
        callback_api_version: CallbackAPIVersion,
        client_id: str,
        clean_session: bool,
    ) -> None: ...

    def username_pw_set(self, username: str, password: str) -> None: ...

    def will_set(
        self,
        topic: str,
        payload: str,
        qos: int,
        retain: bool,
    ) -> None: ...

    def tls_set_context(self, context: ssl.SSLContext) -> None: ...

    def connect_async(self, host: str, port: int, keepalive: int) -> None: ...

    def loop_start(self) -> None: ...

    def subscribe(self, topic: str, qos: int) -> None: ...

    def publish(self, topic: str, payload: str, qos: int, retain: bool) -> None: ...

    def loop_stop(self) -> None: ...

    def disconnect(self) -> None: ...
