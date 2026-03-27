import json
import subprocess
import random
import threading
import time
from datetime import datetime

from generate_task_eval_list import BoxState

# Load configuration from a YAML file
CONFIG_PATH = "bbx_eval_config.yaml"

import yaml
import os
import sys
import cv2


def _load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


_config = _load_config(CONFIG_PATH)

# constants (can be overridden in bbx_eval_config.yaml)
DRY_RUN = _config["DRY_RUN"]
TASK_TIMEOUT = _config["TASK_TIMEOUT"]  # seconds
RECORD_VIDEOS = _config["RECORD_VIDEOS"]
if RECORD_VIDEOS:
    os.makedirs("eval_videos", exist_ok=True)
    VIDEO_DEVICE_INDEX = _config["VIDEO_DEVICE_INDEX"]

# paths
TASK_EVAL_LIST_PATH = _config["TASK_EVAL_LIST_PATH"]
OUTPUT_JSON_PATH = _config["OUTPUT_JSON_PATH"]

# shell commands / clients
SLEEP_COMMAND = _config["SLEEP_COMMAND"]

# New config format supports a list of clients under CLIENTS_TO_EVALUATE.
_raw_clients = _config["CLIENTS_TO_EVALUATE"]

_clients = []
for item in _raw_clients:
    for k, v in item.items():
        _clients.append((k, v))


def load_tally_system(output_json_path):
    """Load the tally system from the output JSON file."""
    with open(output_json_path, "r") as f:
        output_data = json.load(f)
    tally = output_data.get("tally", {})
    notes = output_data.get("notes", [])
    index = output_data.get("index", 0)
    meta = output_data.get("meta", [])
    print(f"Loaded previous evaluation from {output_json_path}:")
    print(f"  - Current index: {index}")
    print(
        f'Last task performed was "{notes[-1]["task_prompt"]}"'
        if notes
        else "No tasks performed yet."
    )
    return tally, notes, index, meta


def start_video_capture(output_path: str, device_index: int):
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video device {device_index}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open video writer for {output_path}")

    stop_event = threading.Event()

    def _capture_loop():
        while not stop_event.is_set():
            ret, frame = cap.read()
            if ret:
                writer.write(frame)
            else:
                time.sleep(0.01)

    thread = threading.Thread(target=_capture_loop, daemon=True)
    thread.start()

    def stop_and_close():
        stop_event.set()
        thread.join(timeout=2.0)
        writer.release()
        cap.release()

    return stop_and_close


if not DRY_RUN:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    helpers_path = os.path.abspath(os.path.join(base_dir, "..", "busybox_utils"))
    if helpers_path not in sys.path:
        sys.path.insert(0, helpers_path)

    from real_aloha_helpers import bringup_robots
    from aloha.constants import LEADER_GRIPPER_JOINT_MID, START_ARM_POSE
    from aloha.robot_utils import move_arms, move_grippers
    _, env = bringup_robots()

    def perform_opening_ceremony():
        print("Performing opening ceremony...")
        start_arm_qpos = START_ARM_POSE[:6]
        move_arms(
            [env.follower_bot_left, env.follower_bot_right],
            [start_arm_qpos] * 4,
            moving_time=2.0,
        )
        move_grippers(
            [env.follower_bot_left, env.follower_bot_right],
            [LEADER_GRIPPER_JOINT_MID] * 2,
            moving_time=0.5,
        )


if __name__ == "__main__":
    # load eval_rollouts from json file
    with open(TASK_EVAL_LIST_PATH, "r") as f:
        eval_data = json.load(f)

    eval_order = eval_data["eval_rollouts"]
    print(
        "Set BusyBox to the initial position as follows:\n"
        + eval_data["meta"]["initial_box_position"]
    )
    input("\n\033[1m\033[93mPress enter when box is ready...\033[0m")

    try:
        tally, notes, index, meta = load_tally_system(OUTPUT_JSON_PATH)
    except FileNotFoundError:
        print(f"Starting new evaluation at {OUTPUT_JSON_PATH}.")
        tally, notes, index, meta = {}, [], 0, []

    session_note = input("\033[1m\033[93mNotes for this evaluation session?\033[0m (press Enter to skip): ").strip()
    meta.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "note": session_note,
        "models": [name for name, _ in _clients],
        "task_count": len(eval_order),
        "task_timeout": TASK_TIMEOUT,
        "start_index": index,
        "task_source": TASK_EVAL_LIST_PATH,
    })

    if index >= len(eval_order):
        print(
            f"All tasks already evaluated (index={index}, total={len(eval_order)}). Nothing to do."
        )
        exit(0)

    # Present configured clients and allow selecting one or 'all'
    print("\nConfigured clients to evaluate:")
    for idx, (name, cmd) in enumerate(_clients):
        print(f"  [{idx}] {name}: {cmd}")
    choice = (
        input(
            "Select client index to evaluate (or type 'all' to run all clients for each task) [all]: "
        )
        .strip()
        .lower()
    )
    if choice == "" or choice == "all":
        selected_clients = list(_clients)
    else:
        selected_clients = [_clients[int(choice)]]

    if not DRY_RUN:
        perform_opening_ceremony()

    box = BoxState()  # to track current box state

    for i, rollout in enumerate(eval_order[index:], start=index):
        task_category = rollout["task_category"]
        task_prompt = rollout.get("task_str") or rollout["task_prompt"]
        init_box_state = rollout["init_box_state"]

        print("\n" + "=" * 40 + "\n")
        # prepare tally buckets per client+category
        for client_name, _ in selected_clients:
            key = f"{client_name}:{task_category}"
            if key not in tally:
                tally[key] = {"success": 0, "fail": 0, "total": 0}

        print(f"Evaluating [{task_category}]: \033[1m\033[93m{task_prompt}\033[0m\n")

        print("Before proceeeding, please set the task's initial state as follows:")
        box.load_from_dict(init_box_state)
        initial_state = str(box)
        print(box)
        input("\nPress Enter to continue...")

        # For each selected client, run the client and collect success/failure
        random.shuffle(selected_clients)
        for client_name, client_cmd in selected_clients:
            print(f'Task "{task_prompt}" executing on client {client_name}...')

            if DRY_RUN:
                print("Dry run mode - skipping task execution.")
            else:
                # Build shell_cmd per client type.
                client_key = client_name.upper()
                if "OPENPI" in client_key:
                    shell_cmd = f'{client_cmd} --args.prompt "{task_prompt}" --args.prompt_timeout {TASK_TIMEOUT}'
                elif "GR00T" in client_key:
                    shell_cmd = f'{client_cmd} -l "{task_prompt}" -t {TASK_TIMEOUT}'
                else:
                    raise ValueError(f"Unknown client type for client {client_name}")

                try:
                    stop_capture = None
                    temp_video_path = None
                    if RECORD_VIDEOS:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        video_path_prefix = f"eval_videos/{i:02d}_{client_name}_{task_category}_{timestamp}_"
                        temp_video_path = f"{video_path_prefix}recording.mp4"
                        stop_capture = start_video_capture(temp_video_path, VIDEO_DEVICE_INDEX)

                    subprocess.run(
                        shell_cmd,
                        shell=True,
                        executable="/bin/bash",
                        check=False,
                    )
                    if stop_capture:
                        stop_capture()
                except KeyboardInterrupt:
                    print("\033[91mInterrupted by user. Continuing evaluation. Press Ctrl+C again to exit.\033[0m")
                except subprocess.TimeoutExpired:
                    if "OPENPI" in client_key:
                        print(
                            f"OpenPI client timed out after {TASK_TIMEOUT} seconds. Treating as valid end of run."
                        )
                    elif "GR00T" in client_key:
                        print(
                            f"GR00T client timed out after {TASK_TIMEOUT} seconds. Treating as valid end of run."
                        )
                    else:
                        raise
                finally:
                    if RECORD_VIDEOS and stop_capture:
                        stop_capture()

            is_rollout_success = (
                input(f"Was the task successful for client {client_name}? (y/n): ")
                .strip()
                .lower()
                == "y"
            )

            if not DRY_RUN:
                perform_opening_ceremony()

            key = f"{client_name}:{task_category}"
            if is_rollout_success:
                tally[key]["success"] += 1
            else:
                tally[key]["fail"] += 1
            tally[key]["total"] += 1

            if RECORD_VIDEOS and temp_video_path:
                final_video_path = f"{video_path_prefix}{is_rollout_success}.mp4"
                try:
                    os.replace(temp_video_path, final_video_path)
                except FileNotFoundError:
                    pass

            note = (
                input(
                    f"Any notes for client {client_name} on this task? (press Enter to skip): "
                )
                .strip()
            )
            notes.append(
                {
                    "client": client_name,
                    "task_category": task_category,
                    "task_prompt": task_prompt,
                    "success": is_rollout_success,
                    "note": note,
                    "index": i,
                    "initial_state": initial_state,
                }
            )

            print(
                f"Tally for client '{client_name}' category '{task_category}': {tally[key]['success']} success, {tally[key]['fail']} fail."
            )

        index = i + 1
        with open(OUTPUT_JSON_PATH, "w") as f:
            json.dump({"tally": tally, "notes": notes, "index": index, "meta": meta}, f, indent=4)

