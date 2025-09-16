#!/usr/bin/env python3
# TODO(dean): remove this top line?

import os
import pprint
from datetime import datetime
import time

from robots.aloha.utils.config import COLLECTION_CONFIG
if COLLECTION_CONFIG['using_instrumented_busybox']:
    from robots.aloha.utils.config import MQTT_TOPICS

from robots.aloha.utils.data_collect_ui import (
    DataCollectUI,
    ArmState,
    RecordState,
    LEFT_PEDAL,
    MIDDLE_PEDAL,
    RIGHT_PEDAL,
)
from robots.aloha.utils.data_collect import EpisodeWriter, create_data_dict
from robots.aloha.utils.robot_utils import opening_ceremony, bringup_robots

from aloha.real_env import get_action
from aloha.constants import IS_MOBILE

FPS = 50  # TODO(dean): import FPS from constants
DELAY_CONSTANT = 0.003


# TODO(dean): consider moving this to robot_utils.py so I can remove aloha.real_env import
def capture_episode_state_machine(
        env,
        ui,
        leader_bot_left,
        leader_bot_right,
        task_info: tuple,
        episode_writer: EpisodeWriter,
        mqtt_client = None,
    ):
    _ = env.reset(fake=True)  # TODO(dean): is this needed?
    observations = []
    observation_timestamps = []
    actions = []
    action_timestamps = []
    # BusyBox instrumentation buffers (populated only if using_instrumented_busybox)
    busybox_states = []  # list[dict] latest BusyBox topic->value snapshot per recorded timestep
    busybox_timestamps = []  # list[float] timestamps aligned with observation acquisition
    actual_dt_history = []
    DT = 1 / FPS
    recorded_fps = None

    total_timesteps = 0
    arm_state = ArmState.ACTIVE
    record_state = RecordState.IDLE

    task_folder, task_instruction = task_info

    # Loop rate is DT only when recording. loop_partial enforces this
    in_loop = True
    while in_loop:
        loop_start = time.time()
        key = ui.get_key()
        # Handle Arm State
        if arm_state == ArmState.ACTIVE:
            t0 = time.time()
            action = get_action(leader_bot_left, leader_bot_right)
            t1 = time.time()
            observation = env.step(action, get_base_vel=IS_MOBILE)
            if key == RIGHT_PEDAL and not record_state == RecordState.RECORDING:
                print("[RIGHT PEDAL] pausing robot teleop")
                arm_state = ArmState.IDLE
                ui.paint_instructions(arm_state, task_instruction, record_state=record_state)
        elif arm_state == ArmState.IDLE:
            if key == RIGHT_PEDAL:
                print("[RIGHT PEDAL] enabling robot teleop")
                arm_state = ArmState.ACTIVE
                ui.paint_instructions(arm_state, task_instruction, record_state=record_state)

        # Handle Record State
        if record_state == RecordState.IDLE:
            reject_recording = False
            if key == LEFT_PEDAL:
                if arm_state == ArmState.ACTIVE:
                    print("[LEFT PEDAL] starting recording")
                    record_state = RecordState.RECORDING
                    ui.paint_instructions(arm_state, task_instruction, record_state=record_state)
                else:
                    print("Robot must be ENABLED to start recording. Press RIGHT foot pedal to enable robot teleop.")
            elif key == MIDDLE_PEDAL:
                print("[MIDDLE PEDAL] refreshing prompt")
                record_state = RecordState.GET_NEW_TASK
        if record_state == RecordState.GET_NEW_TASK:
            # TODO(dean): get new task instruction from task generator
            import random
            task_instruction = random.choice(["Refreshed task instruction", "New task instruction", "Another new task instruction"])
            ui.paint_instructions(arm_state, task_instruction, record_state=record_state)
            record_state = RecordState.IDLE
        elif record_state == RecordState.RECORDING and not arm_state == ArmState.ACTIVE:
            print("Robot teleop has been DISABLED. Pausing recording.")
            record_state = RecordState.IDLE
            ui.paint_instructions(arm_state, task_instruction, record_state=record_state)
        # RECORDING!!
        elif record_state == RecordState.RECORDING and observation is not None:
            if total_timesteps == 0:
                record_start_time = time.time()
            # collect actual data
            observations.append(observation)
            observation_timestamps.append(t1)
            actions.append(action)
            action_timestamps.append(t0)
            if COLLECTION_CONFIG['using_instrumented_busybox'] and mqtt_client is not None:  # recording busybox!
                # Capture a shallow copy of the latest BusyBox state right after obtaining obs/action timestamps.
                # Each entry is a dict logical_topic -> parsed payload (JSON-decoded if possible)
                busybox_states.append(mqtt_client.latest_state())
                busybox_timestamps.append(t1)  # align with observation timestamp
            # end actual data collection
            total_timesteps += 1
            actual_dt_history.append([t0, t1])

            if key == MIDDLE_PEDAL and total_timesteps > 100:
                print("[MIDDLE PEDAL] stopping recording")
                record_state = RecordState.GET_NEW_TASK
                ui.paint_instructions(arm_state, task_instruction, record_state=record_state)
                print(f"Timesteps recorded: {total_timesteps}")
                recorded_fps = total_timesteps / (time.time() - record_start_time)
                print(f"Recorded FPS: {recorded_fps:.2f} (target: {FPS})")
                if COLLECTION_CONFIG['using_instrumented_busybox']:
                    # BusyBox data integration occurs by passing extra kwargs to create_data_dict (updated separately)
                    pass
                data_dict = create_data_dict(
                    actions,
                    action_timestamps,
                    observations,
                    observation_timestamps,
                    COLLECTION_CONFIG['camera_names'],
                    busybox_states=busybox_states if COLLECTION_CONFIG['using_instrumented_busybox'] else None,
                    busybox_timestamps=busybox_timestamps if COLLECTION_CONFIG['using_instrumented_busybox'] else None,
                )
                episode_writer.write_episode(
                    data_dict,
                    task_instruction,
                    task_folder,
                    total_timesteps,
                    recorded_fps,
                    reject_recording
                )
                # exit loop
                in_loop = False

            elif key == RIGHT_PEDAL:
                print("[RIGHT PEDAL] rejecting current recording")
                jj = True
                print(f"Timesteps recorded: {total_timesteps}")
                recorded_fps = total_timesteps / (time.time() - record_start_time)
                print(f"Recorded FPS: {recorded_fps:.2f} (target: {FPS})")
                # exit loop
                in_loop = False

            # this needs to remain at the end of the loop to maintain correct loop timing
            loop_partial = time.time() - loop_start
            time.sleep(max(0, DT - loop_partial - DELAY_CONSTANT))  # maintain loop rate



def main(config):
    # create session folder where episodes will be stored
    current_time = datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    session_dir = f"{config['dataset_dir']}/data_session_{current_time}"
    print(f"Creating session directory: {session_dir}")
    os.makedirs(session_dir, exist_ok=True)

    # create instruction UI
    ui = DataCollectUI()
    ui.create_window()
    ui.paint_instructions("ENABLED", "I am just getting started", record_state=None)
    key = ui.get_key()

    # create task generator
    # task_generator = TaskGenerator(all_knob_turns=all_knob_turns, all_slider_moves=all_slider_moves)

    _, leader_bot_left, leader_bot_right, env = bringup_robots()
    episode_writer = EpisodeWriter(session_dir, config['camera_names'])

    if COLLECTION_CONFIG['using_instrumented_busybox']:
            # Later: integrate mqtt_client.latest_state()/history into data_dict.
            mqtt_client = MqttClient(
                broker=COLLECTION_CONFIG['MQTT_broker'],
                port=COLLECTION_CONFIG['MQTT_port'],
                topics=MQTT_TOPICS,
            )
            mqtt_client.start()

    try:
        while True:
            opening_ceremony(
                leader_bot_left,
                leader_bot_right,
                env.follower_bot_left,
                env.follower_bot_right,
            )
            
            # TODO(dean): get task from task generator Andrey built
            import random
            task_info = ("task_type", random.choice(["Example Task Instruction", "FIRST Another Example Task Instruction"]))

            capture_episode_state_machine(
                env,
                ui,
                leader_bot_left,
                leader_bot_right,
                task_info,
                episode_writer,
                mqtt_client if COLLECTION_CONFIG['using_instrumented_busybox'] else None
            )

    except KeyboardInterrupt:
        print("Session interrupted by user.")
    finally:
        print("Cleaning up and closing session.")
        mqtt_client.stop() if COLLECTION_CONFIG['using_instrumented_busybox'] else None
        # ui.close_window()  # Example: close out things, cleanup


class MqttClient:
    """Lightweight wrapper around paho-mqtt for BusyBox instrumentation.

    Responsibilities:
    - Connect to broker defined in `COLLECTION_CONFIG`.
    - Subscribe to all topics in `MQTT_TOPICS`.
    - Thread-safe buffering of most recent message per topic and an
      append-only history (with optional max length) to allow episode
      integration later.
    - Non-blocking network loop management (start/stop).

    Access patterns:
      latest = client.latest_state()  # dict topic_key -> parsed payload
      history = client.history['buttons']  # list of (timestamp, payload)

    Notes:
    - Payloads are expected to be UTF-8 JSON or simple scalars. We try JSON
      decode first, then fallback to raw text. If bytes cannot decode, store repr.
    - Designed so we can later merge the buffered data into the episode dict
      inside `capture_episode_state_machine` when TODOs are addressed.
    """

    def __init__(self, broker: str, port: int, topics: dict, max_history: int | None = 10_000):
        self.broker = broker
        self.port = port
        self.topics = topics  # mapping logical_name -> mqtt/topic
        self.max_history = max_history
        self._connected = False
        self._client = None
        self._lock = None  # lazy import threading only if used
        self.latest = {k: None for k in self.topics.keys()}
        # history: logical_name -> list[(t, payload_dict_or_value)]
        self.history = {k: [] for k in self.topics.keys()}

    # ------------------------ Public API ------------------------
    def start(self):
        """Create client, connect, subscribe, and start loop in background."""
        try:
            import threading
            import paho.mqtt.client as mqtt
        except ImportError as e:
            raise RuntimeError("paho-mqtt not installed. Add to requirements and pip install.") from e

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
        except Exception as e:
            print(f"[MQTT] Connection error to {self.broker}:{self.port} -> {e}")
            self._client = None
            return
        # start network loop thread
        self._client.loop_start()

    def stop(self):
        if self._client is None:
            return
        try:
            self._client.loop_stop()
            self._client.disconnect()
        finally:
            self._client = None
            self._connected = False

    def latest_state(self):
        with (self._lock or _NullContext()):
            # return a shallow copy to avoid outside mutation
            return dict(self.latest)

    # ---------------------- Internal Callbacks ------------------
    def _on_connect(self, client, userdata, flags, rc):  # noqa: D401
        if rc == 0:
            self._connected = True
            print("[MQTT] Connected to broker.")
            # Subscribe to each topic
            for logical, topic in self.topics.items():
                try:
                    client.subscribe(topic, qos=0)
                    print(f"[MQTT] Subscribed: {logical} -> {topic}")
                except Exception as e:
                    print(f"[MQTT] Failed to subscribe {topic}: {e}")
        else:
            print(f"[MQTT] Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        import json, time as _time
        payload = msg.payload
        try:
            text = payload.decode('utf-8')
        except Exception:
            text = repr(payload)
        # attempt JSON parse
        parsed = None
        if text:
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = text  # keep raw
        logical = self._logical_from_topic(msg.topic)
        if logical is None:
            return  # not one of ours
        ts = _time.time()
        with (self._lock or _NullContext()):
            self.latest[logical] = parsed
            hist = self.history[logical]
            hist.append((ts, parsed))
            if self.max_history is not None and len(hist) > self.max_history:
                # drop oldest (O(n)); for large, consider deque - premature for now
                hist.pop(0)

    # -------------------------- Helpers -------------------------
    def _logical_from_topic(self, topic: str):
        for logical, t in self.topics.items():
            if t == topic:
                return logical
        return None


class _NullContext:
    """Fallback context manager used before threading lock is set."""
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False



if __name__ == "__main__":
    print("Using config:")
    pprint.pprint(COLLECTION_CONFIG, indent=2, width=80, compact=False)
    main(COLLECTION_CONFIG)