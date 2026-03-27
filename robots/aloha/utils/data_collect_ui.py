from enum import Enum, auto

import cv2
import numpy as np


class ArmState(Enum):
    IDLE = auto()
    ACTIVE = auto()

class RecordState(Enum):
    IDLE = auto()
    RECORDING = auto()
    GET_NEW_TASK = auto()

LEFT_PEDAL = ord('a')
MIDDLE_PEDAL = ord('b')
RIGHT_PEDAL = ord('c')


class DataCollectUI:
    def __init__(self):
        self.window_name = "Instructions"

    def create_window(self):
        img = np.zeros((600, 1600, 3), dtype=np.uint8)
        # cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(self.window_name, img)
        cv2.waitKey(1)  # show image
    
    def paint_instructions(self, arm_state, task_instruction, record_state=None):
        return paint_instructions(arm_state, task_instruction, record_state)
    
    def get_key(self, delay=1):
        return cv2.waitKey(delay) & 0xFF


# TODO(dean): make a class out of this
def paint_instructions(arm_state, task_instruction, record_state=None):
    arm_state_print = "IDLE" if arm_state == ArmState.IDLE else "ACTIVE"

    img = np.zeros((600, 1600, 3), dtype=np.uint8)
    # Add instructional text to the image
    row = 100
    if not record_state == RecordState.RECORDING:
        cv2.putText(img, f"Press the RIGHT foot pedal to Enable/Disable Robot. Current State: {arm_state_print}", (10, row), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1)
        row += 100
        cv2.putText(img, "Press the MIDDLE foot pedal to refresh prompt", (10, row), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1)
        row += 100
    else:  # in recording state
        cv2.putText(img, f"Press the RIGHT foot pedal to Reject current recording", (10, row), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1)
        row += 100
        cv2.putText(img, "Press the MIDDLE foot pedal to Stop Recording", (10, row), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1)
        row += 100
    cv2.putText(img, "Press the LEFT foot pedal to Start Recording", (10, row), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1)
    row += 100
    cv2.putText(img, f"INSTRUCTION: {task_instruction}", (10, row), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 1)
    row += 100
    cv2.putText(img, "End Teleop by slowly placing leader arms to resting place and press Ctrl + C", (10, row), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1)
    
    # if recording, draw a recording indicator at the top-right of the instructions image
    if record_state == RecordState.RECORDING:
        _, width = img.shape[:2]
        center = (width - 60, 60)       # 50 pixels inset from the top-right corner
        inner_radius = 30               # Inner filled red circle radius
        outer_radius = 50               # Outer circle gives a 100x100 bounding box
        cv2.circle(img, center, inner_radius, (0, 0, 255), -1)
        cv2.circle(img, center, outer_radius, (0, 0, 255), 2)
       
    cv2.imshow("Instructions", img)
    cv2.waitKey(1)  # show image
    return img