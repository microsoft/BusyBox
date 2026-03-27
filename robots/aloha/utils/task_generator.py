from robots.aloha.utils.control_values import *


flip_switches = []

for sfv in SWITCH_FLAVOR_VALUES:
    for gfv in GRIPPER_FLAVOR_VALUES:
        for sv in SWITCH_VALUES:
            flip_switches.append({"task_type": "FlipSwitch",
                                  "task_instruction": f"Flip the {sfv} switch {'off' if sv == 0 else 'on'} with the {gfv} gripper.", 
                                  "task_goal": {sfv + ' switch': sv}})


push_button = []

for bfv in BUTTON_FLAVOR_VALUES:
    for gfv in GRIPPER_FLAVOR_VALUES:
        push_button.append({"task_type": "PushButton",
                            "task_instruction": f"Push the {bfv} button with the {gfv} gripper.", 
                            "task_goal": {bfv + ' button': 1}})


pull_wire = []

for wfv in WIRE_FLAVOR_VALUES:
    pull_wire.append({"task_type": "PullWire",
                        "task_instruction": f"Pull the {wfv} wire.",
                        "task_goal": {wfv + ' wire': 0}})


insert_wire = []

for wfv in WIRE_FLAVOR_VALUES:
    insert_wire.append({"task_type": "InsertWire",
                        "task_instruction": f"Insert the {wfv} wire.", 
                        "task_goal": {wfv + ' wire': 1}})


move_slider = []

for sfv in SLIDER_FLAVOR_VALUES:
    for sv in SLIDER_EXACT_VALUES:
        move_slider.append({"task_type": "MoveSlider",
                            "task_instruction": f"Move the {sfv} slider to position {sv}.", 
                            "task_goal": {sfv + ' slider': sv}})


turn_knob = []

for kfv in KNOB_EXACT_VALUES:
    turn_knob.append({"task_type": "TurnKnob",
                      "task_instruction": f"Turn the knob to position {kfv}.",
                      "task_goal": {'knob': kfv}})


reposition_raw = [
    ("Close both grippers.", {}), 
    ("Close left gripper.", {}),
    ("Close right gripper.", {}),
    ("Move the left gripper to the left.", {}),
    ("Move the left gripper to the right.", {}),
    ("Move the right gripper to the left.", {}),
    ("Move the right gripper to the right.", {}),
    ("Open both grippers.", {}),
    ("Open left gripper.", {}),
    ("Open right gripper.", {}),
    ("Return to the home position.", {}),
    ("View the box from the top.", {})
]

reposition = []

for task in reposition_raw:
    reposition.append({"task_type": "Reposition",
                                "task_instruction": task[0],
                                "task_goal": task[1]})
    

move_box_raw = [
    ("Move the box away.", {}),
    ("Move the box closer.", {}),
    ("Move the box to the left.", {}),
    ("Move the box to the right.", {}),
    ("Rotate the box clockwise.", {}),
    ("Rotate the box counterclockwise.", {})
]

move_box = []

for task in move_box_raw:
    move_box.append({"task_type": "MoveBox",
                        "task_instruction": task[0],
                        "task_goal": task[1]})


# sample 10 tasks from each category

import random
import json

def generate_tasks():
    ###all_tasks = flip_switches + push_button + pull_wire + insert_wire + move_slider + turn_knob + reposition + move_box
    #### For now, exclude the repositioning tasks --- we don't need more data for them.
    # all_tasks =  flip_switches + push_button + pull_wire + insert_wire + move_slider + turn_knob + move_box
    #### For extra data for the following tasks: 
    # all_tasks = pull_wire + turn_knob  # wave 3
    all_tasks = flip_switches + push_button + pull_wire + insert_wire + move_slider + turn_knob  # corrective actions
    for i, task in enumerate(all_tasks):
        task['task_id'] = i + 1
    return all_tasks


def sample_with_resample(population, k):
    if len(population) >= k:
        return random.sample(population, k)
    else:
        return random.choices(population, k=k)

sampled_tasks = {
    "flip_switches": sample_with_resample(flip_switches, 10),
    "push_button": sample_with_resample(push_button, 10),
    "pull_wire": sample_with_resample(pull_wire, 10),
    "insert_wire": sample_with_resample(insert_wire, 10),
    "move_slider": sample_with_resample(move_slider, 10),
    "turn_knob": sample_with_resample(turn_knob, 10),
}

# create a fully shuffled order of all sampled tasks, one entry per task
sample_order = [[category, task] for category, tasks in sampled_tasks.items() for task in tasks]
random.shuffle(sample_order)
sampled_tasks["eval_order"] = sample_order

with open("/home/aloha/dean/sampled_tasks.json", "w") as f:
    json.dump(sampled_tasks, f, indent=4)

