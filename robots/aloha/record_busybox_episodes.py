#!/usr/bin/env python3
# TODO(dean): remove this top line?

import os
import pprint
from datetime import datetime
import time

from robots.aloha.utils.config import COLLECTION_CONFIG
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
    ):
    _ = env.reset(fake=True)  # TODO(dean): is this needed?
    observations = []
    observation_timestamps = []
    actions = []
    action_timestamps = []
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
            if COLLECTION_CONFIG['using_instrumented_busybox']:  # recording busybox!
                # TODO(dean): start a process to listen to MQTT messages and store them
                pass
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
                    # TODO(dean): incorporate busybox state data into data_dict somehow
                    pass
                data_dict = create_data_dict(
                    actions,
                    action_timestamps,
                    observations,
                    observation_timestamps,
                    COLLECTION_CONFIG['camera_names']
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

    node, leader_bot_left, leader_bot_right, env = bringup_robots()
    episode_writer = EpisodeWriter(session_dir, config['camera_names'])

    episode_count = 0
    total_rejects = 0
    reject_recording = False
    
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

            capture_episode_state_machine(env, ui, leader_bot_left, leader_bot_right, task_info, episode_writer)

    except KeyboardInterrupt:
        print("Session interrupted by user.")
    finally:
        print("Cleaning up and closing session.")
        # ui.close_window()  # Example: close out things, cleanup


if __name__ == "__main__":
    print("Using config:")
    pprint.pprint(COLLECTION_CONFIG, indent=2, width=80, compact=False)
    main(COLLECTION_CONFIG)