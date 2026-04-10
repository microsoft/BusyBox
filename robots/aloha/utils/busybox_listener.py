"""BusyBoxListener: lightweight MQTT instrumentation listener for BusyBox.

Extracted and renamed from former MqttClient class inside
`record_busybox_episodes.py` to improve modularity and reuse.

Responsibilities:
- Connect to MQTT broker defined externally (see COLLECTION_CONFIG)
- Subscribe to given topics mapping logical_name -> mqtt/topic
- Maintain thread-safe latest snapshot and append-only history per topic
- Provide shallow-copy access to latest state for integration during
  episode data collection.

Typical usage:

    from robots.aloha.utils.busybox_listener import BusyBoxListener
    listener = BusyBoxListener(broker, port, topics)
    listener.start()
    # ... during loop ...
    latest = listener.latest_state()
    # ... on shutdown ...
    listener.stop()

Notes:
- Payloads are expected to be UTF-8 JSON or simple scalars. We attempt
  JSON decode, fallback to raw text / repr on decode failure.
- History truncation is O(n) when over capacity; if this becomes a perf
  bottleneck we can swap in collections.deque.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
import json
import time


class BusyBoxListener:
    def __init__(
        self,
        broker: str,
        port: int,
        topics: Dict[str, str],
        max_history: Optional[int] | None = 10_000,
    ) -> None:
        self.broker = broker
        self.port = port
        self.topics = topics  # mapping logical_name -> mqtt/topic
        self.max_history = max_history
        self._connected = False
        self._client = None
        self._lock = None  # lazy import threading only if used
        self.latest: Dict[str, Any] = {k: None for k in self.topics.keys()}
        # history: logical_name -> list[(t, payload)]
        self.history: Dict[str, List[Tuple[float, Any]]] = {k: [] for k in self.topics.keys()}

    # ------------------------ Public API ------------------------
    def start(self) -> None:
        """Create client, connect, subscribe, and start loop in background."""
        try:
            import threading
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError as e:  # pragma: no cover - runtime safeguard
            raise RuntimeError(
                "paho-mqtt not installed. Add it to requirements.txt and pip install."
            ) from e

        if self._client is not None:
            return  # already started
        self._lock = threading.RLock()
        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        # Optional: faster reconnect attempts
        self._client.reconnect_delay_set(min_delay=1, max_delay=8)
        try:
            self._client.connect(self.broker, self.port, keepalive=30)
        except Exception as e:  # pragma: no cover - network specific
            print(f"[BusyBoxListener] Connection error to {self.broker}:{self.port} -> {e}")
            self._client = None
            return
        # start network loop thread
        self._client.loop_start()

        # Wait up to 2s for first messages on each topic
        deadline = time.time() + 2.0

        # First, allow time for the on_connect callback to run and subscriptions to establish
        while time.time() < deadline and not self._connected:
            time.sleep(0.05)

        # Then wait (remaining time) for at least one message per topic
        while time.time() < deadline:
            with (self._lock or _NullContext()):
                if all(v is not None for v in self.latest.values()):
                    break
                time.sleep(0.05)

        with (self._lock or _NullContext()):
            missing = [k for k, v in self.latest.items() if v is None]

        if missing:
            print(f"[BusyBoxListener] [WARNING]: no messages received within 2s for: {', '.join(missing)}")
        else:
            print("[BusyBoxListener] All topics produced at least one message within 2s.")

    def stop(self) -> None:
        if self._client is None:
            return
        try:
            self._client.loop_stop()
            self._client.disconnect()
        finally:
            self._client = None
            self._connected = False

    def latest_state(self) -> Dict[str, Any]:
        with (self._lock or _NullContext()):
            # Return a shallow copy to avoid external mutation.
            return dict(self.latest)

    # ---------------------- Internal Callbacks ------------------
    def _on_connect(self, client, userdata, flags, rc):  # noqa: D401
        if rc == 0:
            self._connected = True
            print("[BusyBoxListener] Connected to broker.")
            # Subscribe to each topic
            for logical, topic in self.topics.items():
                try:
                    client.subscribe(topic, qos=0)
                    print(f"[BusyBoxListener] Subscribed: {logical} -> {topic}")
                except Exception as e:  # pragma: no cover
                    print(f"[BusyBoxListener] Failed to subscribe {topic}: {e}")
        else:
            print(f"[BusyBoxListener] Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):  # noqa: D401
        payload = msg.payload
        try:
            text = payload.decode("utf-8")
        except Exception:
            text = repr(payload)
        # Attempt JSON parse
        if text:
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = text  # keep raw
        else:
            parsed = text
        logical = self._logical_from_topic(msg.topic)
        if logical is None:
            return  # not one of ours
        ts = time.time()
        with (self._lock or _NullContext()):
            self.latest[logical] = parsed
            hist = self.history[logical]
            hist.append((ts, parsed))
            if self.max_history is not None and len(hist) > self.max_history:
                hist.pop(0)  # O(n) trim

    # -------------------------- Helpers -------------------------
    def _logical_from_topic(self, topic: str):
        for logical, t in self.topics.items():
            if t == topic:
                return logical
        return None


class _NullContext:
    """Fallback context manager used before threading lock is set."""

    def __enter__(self):  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
        return False
