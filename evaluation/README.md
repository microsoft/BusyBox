# bbx_eval

Evaluation harness for running BusyBox task rollouts on **Mobile ALOHA** (real robot) and logging results.

This folder contains a small, opinionated “human-in-the-loop” evaluator:
- It **launches one or more robot policy clients** (via shell commands),
- Presents a task prompt + required initial BusyBox state,
- Optionally records a webcam video,
- Asks a human to mark **success/fail** and add notes,
- Writes a running tally to a JSON results file.

> Important: **`bbx_eval_config.yaml` and `eval_bbx_client.py` are custom to our lab’s Mobile ALOHA + BusyBox setup.**
> Other researchers should treat this as a *reference implementation* and adapt:
> - robot bringup and reset (“opening ceremony”),
> - how tasks are sent to their client(s),
> - camera/video capture,
> - and any safety/timeouts.

---

## Files

- `generate_task_eval_list.py`: creates a randomized evaluation list in `eval_rollouts.json`.
- `bbx_eval_config.yaml`: evaluation config (timeouts, video recording, and how clients are launched).
- `eval_bbx_client.py`: main evaluation loop (reads rollouts, runs clients, records videos, prompts for labels).

---

## Quickstart (general flow)

### 1) Generate an evaluation rollout list

From this directory:

```bash
cd /home/aloha/dean/bbx_eval
python3 generate_task_eval_list.py
```

This writes `eval_rollouts.json` with:
- `meta`: info like seed and number of tasks
- `eval_rollouts`: a shuffled list of tasks
  - `task_prompt` / `task_category` / `target`
  - `init_box_state`: the BusyBox state you should set before running the task

If you want a different mix of tasks or counts, edit the parameters near the bottom of `generate_task_eval_list.py` (seed, task types, samples per task).

### 2) Configure evaluation settings + client launch commands

Edit `bbx_eval_config.yaml`:

- **General**
  - `DRY_RUN`: if `true`, skips actually launching clients (still walks through prompts)
  - `TASK_TIMEOUT`: prompt timeout passed through to the clients (per-task)

- **Video**
  - `RECORD_VIDEOS`: enable/disable webcam capture
  - `VIDEO_DEVICE_INDEX`: OpenCV camera index (often `0`)

- **Paths**
  - `TASK_EVAL_LIST_PATH`: usually `eval_rollouts.json`
  - `OUTPUT_JSON_PATH`: output results file (e.g. `eval_results.json`)

- **Robot**
  - `SLEEP_COMMAND`: command to put the robot in a safe state before starting (lab-specific)

- **Clients**
  - `CLIENTS_TO_EVALUATE`: a list of named clients, each specified as a shell command string.

### 3) Run the evaluator

```bash
cd /home/aloha/dean/bbx_eval
python3 eval_bbx_client.py
```

What you’ll see:
1. A prompt to place the BusyBox in the configured initial pose.
2. (Optional) It loads `OUTPUT_JSON_PATH` if it exists to **resume** from the saved `index`.
3. It prints configured clients and asks you to run **one client** or **all**.
4. For each rollout:
   - It prints the task prompt.
   - It prints the required initial BusyBox state (sliders, wires, switches, knob).
   - It launches the selected client(s) for that task.
   - It asks you to mark success/fail and optionally enter notes.

Outputs:
- Results JSON written to `OUTPUT_JSON_PATH` with keys:
  - `tally`: per-client and per-task-category counts
  - `notes`: per-trial annotations (prompt, category, success, freeform notes)
  - `index`: resume pointer
  - `meta`: session metadata (timestamp, models, etc.)
- Videos (if enabled) saved under `eval_videos/` with filenames like:
  - `<taskIndex>_<clientName>_<taskCategory>_<timestamp>_<True|False>.mp4`

---

## Notes on customization (for other robots / labs)

This code is **not a general-purpose evaluation framework**. It assumes:
- **Mobile ALOHA** hardware and a specific bringup/reset routine.
- Policy clients that can accept a natural-language task prompt with a timeout.
- A local webcam accessible via OpenCV for recording.

To adapt elsewhere, you’ll likely want to modify:
- `perform_opening_ceremony()` in `eval_bbx_client.py` (robot reset / safe pose).
- Client command invocation + CLI flags (how tasks are transmitted).
- Video recording (device selection, framerate, resolution, multi-camera, etc.).
- Safety: e-stops, timeouts, collision constraints, and failure handling.

---

## Troubleshooting

- **Camera won’t open**: set `VIDEO_DEVICE_INDEX` to the correct camera, or set `RECORD_VIDEOS: false`.
- **Client doesn’t receive the prompt**: verify your `CLIENTS_TO_EVALUATE` command runs standalone, then confirm the appended flags match your client’s CLI.
- **Resume behavior**: if `OUTPUT_JSON_PATH` exists, evaluation resumes from its saved `index`. Delete/rename the file to start fresh.
