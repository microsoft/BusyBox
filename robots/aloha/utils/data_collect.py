import os
import time
import json
import h5py
import pyfiglet  # TODO(dean): what exactly does this do? Can we remove?
import random
import numpy as np
from datetime import datetime
import cv2

from robots.aloha.utils.smart_task_selector import SmartTaskSelector
from robots.aloha.utils.config import TASKBOX_TASKS

from aloha.constants import IS_MOBILE

def create_data_dict(
        actions,
        action_timestamps,
        observations,
        observation_timestamps,
        camera_names
    ):
    """
    For each timestep:
    observations
    - images
        - cam_high          (480, 640, 3) 'uint8'
        - cam_low           (480, 640, 3) 'uint8'   (on Stationary)
        - cam_left_wrist    (480, 640, 3) 'uint8'
        - cam_right_wrist   (480, 640, 3) 'uint8'
    - qpos                  (14,)         'float64'
    - qvel                  (14,)         'float64'

    action                  (14,)         'float64'
    """

    data_dict = {
        '/observations/qpos': [],
        '/observations/qvel': [],
        '/observations/effort': [],
        '/observations/timestamp': [],
        '/action': [],
        '/action_timestamp': [],
    }
    for cam_name in camera_names:
        data_dict[f'/observations/images/{cam_name}'] = []

    # len(action): max_observations, len(time_steps): max_observations + 1
    while actions:
        action = actions.pop(0)
        action_ts = action_timestamps.pop(0)
        obs = observations.pop(0)
        obs_ts = observation_timestamps.pop(0)
        data_dict['/observations/qpos'].append(obs.observation['qpos'])
        data_dict['/observations/qvel'].append(obs.observation['qvel'])
        data_dict['/observations/effort'].append(obs.observation['effort'])
        data_dict['/observations/timestamp'].append(obs_ts)
        data_dict['/action'].append(action)
        data_dict['/action_timestamp'].append(action_ts)
        for cam_name in camera_names:
            data_dict[f'/observations/images/{cam_name}'].append(
                obs.observation['images'][cam_name]
            )
    return data_dict

class EpisodeWriter:
    def __init__(self, dataset_path, camera_names, n = 0, compress=True):
        #self.dataset_path = dataset_path
        self.n = n
        self.camera_names = camera_names
        # self.session_folder = session_folder
        self.COMPRESS = compress
        self.manifest_json = {
                    "version": 1.0,
                    "collector's notes": " ",
                }
        self.total_rejects = 0
        # saving dataset
        # if not os.path.isdir(dataset_dir):
            # os.makedirs(dataset_dir)
        # dataset_path = os.path.join(dataset_dir, session_folder)
        if not os.path.isdir(dataset_path):
            os.makedirs(dataset_path)
        self.dataset_path = dataset_path
        
        manifest_path = os.path.join(self.dataset_path, 'manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump({}, f)

    def write_episode(self, data_dict,
                      task_instruction,
                      task_folder,
                      total_timesteps,
                      recorded_fps,
                      reject_recording, n=None):
        if n is None:
            n = self.n
        self.n += 1
        
        if self.COMPRESS:
            # JPEG compression
            t0 = time.time()
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]  # tried as low as 20, seems fine
            compressed_len = []
            for cam_name in self.camera_names:
                image_list = data_dict[f'/observations/images/{cam_name}']
                compressed_list = []
                compressed_len.append([])
                for image in image_list:
                    # 0.02 sec # cv2.imdecode(encoded_image, 1)
                    result, encoded_image = cv2.imencode('.jpg', image, encode_param)
                    compressed_list.append(encoded_image)
                    compressed_len[-1].append(len(encoded_image))
                data_dict[f'/observations/images/{cam_name}'] = compressed_list
            print(f'compression: {time.time() - t0:.2f}s')

            # pad so it has same length
            t0 = time.time()
            compressed_len = np.array(compressed_len)
            padded_size = compressed_len.max()
            for cam_name in self.camera_names:
                compressed_image_list = data_dict[f'/observations/images/{cam_name}']
                padded_compressed_image_list = []
                for compressed_image in compressed_image_list:
                    padded_compressed_image = np.zeros(padded_size, dtype='uint8')
                    image_len = len(compressed_image)
                    padded_compressed_image[:image_len] = compressed_image
                    padded_compressed_image_list.append(padded_compressed_image)
                data_dict[f'/observations/images/{cam_name}'] = padded_compressed_image_list
            print(f'padding: {time.time() - t0:.2f}s')

        # Save Manifest
        t0 = time.time()
        task_folder_path = os.path.join(self.dataset_path, task_folder)
        if not os.path.isdir(task_folder_path):
            os.makedirs(task_folder_path)
        episode_path = os.path.join(task_folder_path, f'episode_{n}.hdf5')
        self.manifest_json[f'episode_{n}'] = {
            'task_folder': os.path.join(self.dataset_path, task_folder),
            'task_instruction': task_instruction,
            'timesteps': total_timesteps,
            'recorded_fps': recorded_fps,
            'success': not reject_recording,
        }
        n += 1
        if reject_recording:
            self.total_rejects += 1
        with open(os.path.join(self.dataset_path, 'manifest.json'), 'w') as f:
            json.dump(self.manifest_json, f, indent=4)
        # HDF5
        with h5py.File(episode_path, 'w', rdcc_nbytes=1024**2*2) as root:
            root.attrs['sim'] = False
            root.attrs['compress'] = self.COMPRESS
            obs = root.create_group('observations')
            image = obs.create_group('images')
            for cam_name in self.camera_names:
                if self.COMPRESS:
                    _ = image.create_dataset(cam_name, (total_timesteps, padded_size), dtype='uint8',
                                            chunks=(1, padded_size), )
                else:
                    _ = image.create_dataset(cam_name, (total_timesteps, 480, 640, 3), dtype='uint8',
                                            chunks=(1, 480, 640, 3), )
            _ = obs.create_dataset('qpos', (total_timesteps, 14))
            _ = obs.create_dataset('qvel', (total_timesteps, 14))
            _ = obs.create_dataset('effort', (total_timesteps, 14))
            # timestamps (were missing, causing KeyError when writing)
            _ = obs.create_dataset('timestamp', (total_timesteps,), dtype='float64')
            _ = root.create_dataset('action', (total_timesteps, 14))
            _ = root.create_dataset('action_timestamp', (total_timesteps,), dtype='float64')
            if IS_MOBILE:
                _ = root.create_dataset('base_action', (total_timesteps, 2))

            for name, array in data_dict.items():
                # Allow leading '/' in keys
                ds_path = name[1:] if name.startswith('/') else name
                # Ensure intermediate groups exist if using nested paths
                if '/' in ds_path:
                    grp_path, ds_name = ds_path.rsplit('/', 1)
                    if grp_path not in root:
                        # create missing group hierarchy
                        current = root
                        for part in grp_path.split('/'):
                            if part not in current:
                                current = current.create_group(part)
                            else:
                                current = current[part]
                else:
                    ds_name = ds_path
                    grp_path = ''
                full_path = ds_path
                if full_path not in root:
                    arr_np = np.asarray(array)
                    root.create_dataset(full_path, data=arr_np, maxshape=arr_np.shape)
                else:
                    root[full_path][...] = array

            if self.COMPRESS:
                _ = root.create_dataset('compress_len', (len(self.camera_names), total_timesteps))
                root['/compress_len'][...] = compressed_len

        print(f'Saving: {time.time() - t0:.1f} secs')
        print(f"Episode saved to {episode_path}")

        print(pyfiglet.figlet_format(f'{n} episodes recorded!'))
        return True
    
class TaskGenerator:
    def __init__(self, task_type=None, all_knob_turns=False, all_slider_moves=False):
        self.task_type = task_type
        self._last_slider_task = None

        self.all_knob_turns = all_knob_turns
        self.all_slider_moves = all_slider_moves


        self.turns = None


        self.top_slider_moves = None
        self.bottom_slider_moves = None
        if self.all_slider_moves:
            starting_position = 1
            number_of_positions = 5
            self.top_slider_moves = SmartTaskSelector.generate_turn_sequence(number_of_positions, starting_position)
            self.bottom_slider_moves = SmartTaskSelector.generate_turn_sequence(number_of_positions, starting_position)

    def generate_next_task(self):
        if self.all_knob_turns:
            if not self.turns:
                starting_position = 1
                number_of_positions = 6
                self.turns = SmartTaskSelector.generate_turn_sequence(number_of_positions, starting_position)

            next_task = self.turns.pop(0)
            print(f"You should be starting at position {next_task[0]} and turning to {next_task[1]}")
            task_folder = "TurnKnob"
            task_instruction = f"Turn the knob to position {next_task[1]}"
        elif self.all_slider_moves:
            if not self.top_slider_moves and not self.bottom_slider_moves:
                starting_position = 1
                number_of_positions = 5
                self.top_slider_moves = SmartTaskSelector.generate_turn_sequence(number_of_positions, starting_position)
                self.bottom_slider_moves = SmartTaskSelector.generate_turn_sequence(number_of_positions, starting_position)
            if self.top_slider_moves:
                next_task = self.top_slider_moves.pop(0)
                print(f"You should be starting at position {next_task[0]} and moving to {next_task[1]}")
                task_folder = "MoveSlider"
                task_instruction = f"Move the top slider to position {next_task[1]}"
            elif self.bottom_slider_moves:
                next_task = self.bottom_slider_moves.pop(0)
                print(f"You should be starting at position {next_task[0]} and moving to {next_task[1]}")
                task_folder = "MoveSlider"
                task_instruction = f"Move the bottom slider to position {next_task[1]}"
        else:
            if self.task_type is not None:
                task_folder, task_instruction = self.select_random_taskbox_task_given_type(self.task_type)
            else:
                task_folder, task_instruction = self.generate_task()
            
        return task_folder, task_instruction



    def select_random_taskbox_task_given_type(self, task_type):
        # Fix the iteration over TASKBOX_TASKS dictionary
        tasks_of_type = [(task_folder, task_instruction) for task_id, (task_folder, task_instruction) in TASKBOX_TASKS.items() if task_folder == task_type]
        print(f"Tasks of type {task_type}:", tasks_of_type)
        return random.choice(tasks_of_type)
    
    def generate_task(self):
        np.random.seed(int(datetime.now().timestamp()))
        task_type = np.random.choice(
            [
            "PullWire",
            "InsertWire",
            "PushButton",
            "MoveSlider",
            "TurnKnob",
            "FlipSwitch",
            "Reposition",
            "MoveBox",
            ]
        )
        return self.select_random_taskbox_task_given_type(task_type)
