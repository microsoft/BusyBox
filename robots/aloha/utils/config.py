import os

DATA_DIR = os.path.expanduser('~/aloha_data')
COLLECTION_CONFIG = {
    'dataset_dir': DATA_DIR + '/busybox_collection',
    'camera_names': ['cam_high', 'cam_left_wrist', 'cam_right_wrist'],
    'using_instrumented_busybox': True,  # requires BusyBox to publish to MQTT
    'MQTT_broker': 'localhost',
    'MQTT_port': 1883,
}

MQTT_TOPICS = {
    'buttons': 'busybox/buttons/state',
    'knob': 'busybox/knob/state',
    'sliders': 'busybox/sliders/state',
    'switches': 'busybox/switches/state',
    'wires': 'busybox/wires/state',
}

TASKBOX_TASKS = {
    # PullWire instructions
    1: ("PullWire", "Pull the red wire."),
    2: ("PullWire", "Pull the blue wire."),
    3: ("PullWire", "Pull the black wire."),
    4: ("PullWire", "Pull the white wire."),

    # InsertWire instructions
    5: ("InsertWire", "Insert the red wire."),
    6: ("InsertWire", "Insert the blue wire."),
    7: ("InsertWire", "Insert the black wire."),
    8: ("InsertWire", "Insert the white wire."),

    # PushButton instructions
    9: ("PushButton", "Push the blue button."),
    10: ("PushButton", "Push the yellow button."),
    11: ("PushButton", "Push the green button."),
    12: ("PushButton", "Push the red button."),

    # MoveSlider instructions
    13: ("MoveSlider", "Move the top slider to position 1."),
    14: ("MoveSlider", "Move the top slider to position 2."),
    15: ("MoveSlider", "Move the top slider to position 3."),
    16: ("MoveSlider", "Move the top slider to position 4."),
    17: ("MoveSlider", "Move the top slider to position 5."),
    18: ("MoveSlider", "Move the bottom slider to position 1."),
    19: ("MoveSlider", "Move the bottom slider to position 2."),
    20: ("MoveSlider", "Move the bottom slider to position 3."),
    21: ("MoveSlider", "Move the bottom slider to position 4."),
    22: ("MoveSlider", "Move the bottom slider to position 5."),

    # TurnKnob instructions
    23: ("TurnKnob", "Turn the knob to position 1."),
    24: ("TurnKnob", "Turn the knob to position 2."),
    25: ("TurnKnob", "Turn the knob to position 3."),
    26: ("TurnKnob", "Turn the knob to position 4."),
    27: ("TurnKnob", "Turn the knob to position 5."),
    28: ("TurnKnob", "Turn the knob to position 6."),

    # Flip Switch instructions
    29: ("FlipSwitch", "Flip the top switch on with the left gripper."),
    30: ("FlipSwitch", "Flip the top switch on with the right gripper."),
    31: ("FlipSwitch", "Flip the top switch off with the left gripper."),
    32: ("FlipSwitch", "Flip the top switch off with the right gripper."),
    33: ("FlipSwitch", "Flip the bottom switch on with the left gripper."),
    34: ("FlipSwitch", "Flip the bottom switch on with the right gripper."),
    35: ("FlipSwitch", "Flip the bottom switch off with the left gripper."),
    36: ("FlipSwitch", "Flip the bottom switch off with the right gripper."),
}

NON_TASKBOX_TASKS = {
    # Go to position instructions
    41: ("Reposition", "Return to the home position."),
    42: ("Reposition", "View the box from the top."),
    43: ("Reposition", "Open left gripper."),
    44: ("Reposition", "Open right gripper."),
    45: ("Reposition", "Open both grippers."),
    46: ("Reposition", "Close left gripper."),
    47: ("Reposition", "Close right gripper."),
    48: ("Reposition", "Close both grippers."),
    49: ("Reposition", "Move the left gripper to the left."),
    50: ("Reposition", "Move the left gripper to the right."),
    51: ("Reposition", "Move the right gripper to the left."),
    52: ("Reposition", "Move the right gripper to the right."),

    # Move box instructions
    53: ("MoveBox", "Move the box to the left."),
    54: ("MoveBox", "Move the box to the right."),
    55: ("MoveBox", "Move the box away."),
    56: ("MoveBox", "Move the box closer."),
    57: ("MoveBox", "Rotate the box clockwise."),
    58: ("MoveBox", "Rotate the box counterclockwise."),
}