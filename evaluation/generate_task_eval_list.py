import random
from pprint import pprint
import re
from typing import TypeAlias


flip_switch = [
    "Flip the bottom switch off with the left gripper",
    "Flip the bottom switch off with the right gripper",
    "Flip the bottom switch on with the left gripper",
    "Flip the bottom switch on with the right gripper",
    "Flip the top switch off with the left gripper",
    "Flip the top switch off with the right gripper",
    "Flip the top switch on with the left gripper",
    "Flip the top switch on with the right gripper",
]
# insert_wire = [
#     "Insert the black wire.",
#     "Insert the blue wire.",
#     "Insert the red wire.",
#     "Insert the white wire.",
# ]
move_bb = [
    "Rotate the box counterclockwise.",
    "Move the box away.",
    "Move the box closer.",
    "Move the box to the left.",
    "Rotate the box clockwise.",
    "Move the box to the right.",
]
move_slider = [
    "Move the bottom slider to position 1.",
    "Move the bottom slider to position 2.",
    "Move the bottom slider to position 3.",
    "Move the bottom slider to position 4.",
    "Move the bottom slider to position 5.",
    "Move the top slider to position 1.",
    "Move the top slider to position 2.",
    "Move the top slider to position 3.",
    "Move the top slider to position 4.",
    "Move the top slider to position 5.",
]
pull_wire = [
    "Pull the black wire.",
    "Pull the blue wire.",
    "Pull the red wire.",
    "Pull the white wire.",
]
push_button = [
    "Push the blue button with the left gripper.",
    "Push the blue button with the right gripper.",
    "Push the green button with the left gripper.",
    "Push the green button with the right gripper.",
    "Push the red button with the left gripper.",
    "Push the red button with the right gripper.",
    "Push the yellow button with the left gripper.",
    "Push the yellow button with the right gripper.",
]
turn_knob = [
    "Turn the knob to position 3.",
    "Turn the knob to position 1.",
    "Turn the knob to position 5.",
    "Turn the knob to position 6.",
    "Turn the knob to position 2.",
    "Turn the knob to position 4.",
]

Target: TypeAlias = int | str | None

class BoxState:
    """Class to represent the state of the box."""
    def __init__(self):
        self.sliders = {"top": 1, "bottom": 1}
        self.wires_inserted = {"black": True, "blue": True, "red": True, "white": True}
        self.switches = {"top": True, "bottom": True}
        self.knob_position = 1

    def update_slider(self, slider_id, position):
        self.sliders[slider_id] = position

    def update_wire(self, wire_color, inserted):
        self.wires_inserted[wire_color] = inserted

    def update_switch(self, switch_id, state):
        self.switches[switch_id] = state

    def update_knob(self, position):
        self.knob_position = position

    def randomize_box(self):
        self.sliders["top"] = random.randint(1, 5)
        self.sliders["bottom"] = random.randint(1, 5)
        for color in self.wires_inserted:
            self.wires_inserted[color] = random.choice([True, False])
        self.switches["top"] = random.choice([True, False])
        self.switches["bottom"] = random.choice([True, False])
        self.knob_position = random.randint(1, 6)

        return self.to_dict()

    def generate_valid_state(self, eval_rollout: dict) -> dict:
        """Generate a valid box state for an eval rollout.

        Args:
            eval_rollout: Dictionary with keys "task_str", "task_category", and "target"
                - task_str: original instruction string
                - task_category: one of task types (e.g. "move_slider")
                - target: parsed target from parse_target()

        Returns:
            dict box state suitable as a state for the rollout.
        """

        task_prompt = eval_rollout["task_prompt"]
        task_category = eval_rollout["task_category"]
        target = eval_rollout["target"]

        if not isinstance(task_prompt, str):
            raise TypeError(f"eval_rollout[0] (task_prompt) must be str; got {type(task_prompt).__name__}: {task_prompt!r}")
        if not isinstance(task_category, str):
            raise TypeError(
                f"eval_rollout[1] (task_category) must be str; got {type(task_category).__name__}: {task_category!r}"
            )

        if task_category == "move_slider":
            # Set the specified slider to a different position than the target
            if not isinstance(target, int):
                raise TypeError(
                    f"For task_category='move_slider', target must be int; got {type(target).__name__}: {target!r}"
                )
            task_lc = task_prompt.lower()
            slider_id = "top" if "top" in task_lc else "bottom"
            while self.sliders[slider_id] == target:
                self.sliders[slider_id] = random.randint(1, 5)
            self.update_slider(slider_id, self.sliders[slider_id])
        elif task_category == "insert_wire":
            # Ensure the specified wire is not inserted
            self.update_wire(target, False)
        elif task_category == "pull_wire":
            # Ensure the specified wire is inserted
            self.update_wire(target, True)
        elif task_category == "flip_switch":
            # Set the specified switch to the opposite state
            task_lc = task_prompt.lower()
            switch_id = "top" if "top" in task_lc else "bottom"
            opposite_state = not (target == "on")
            self.update_switch(switch_id, opposite_state)
        elif task_category == "turn_knob":
            # Set knob to a different position than the target
            if not isinstance(target, int):
                raise TypeError(
                    f"For task_category='turn_knob', target must be int; got {type(target).__name__}: {target!r}"
                )
            while self.knob_position == target:
                self.knob_position = random.randint(1, 6)
            self.update_knob(self.knob_position)
        return self.to_dict()

    def update_assuming_task_performed(self, eval_rollout: dict) -> dict:
        """Update internal state assuming the rollout task was successfully performed.

        This mutates the current BoxState (expected to already be in the rollout's
        initial state) and returns the resulting state dict.

        Expected eval_rollout keys:
            - task_str: str
            - task_category: str
            - target: int | str | None (as produced by parse_target)
        """

        task_str = eval_rollout["task_str"]
        task_category = eval_rollout["task_category"]
        target = eval_rollout["target"]

        if not isinstance(task_str, str):
            raise TypeError(f"eval_rollout['task_str'] must be str; got {type(task_str).__name__}: {task_str!r}")
        if not isinstance(task_category, str):
            raise TypeError(
                f"eval_rollout['task_category'] must be str; got {type(task_category).__name__}: {task_category!r}"
            )

        if task_category == "move_slider":
            if not isinstance(target, int):
                raise TypeError(
                    f"For task_category='move_slider', target must be int; got {type(target).__name__}: {target!r}"
                )
            task_lc = task_str.lower()
            slider_id = "top" if "top" in task_lc else "bottom"
            self.update_slider(slider_id, target)

        elif task_category == "insert_wire":
            if not isinstance(target, str):
                raise TypeError(
                    f"For task_category='insert_wire', target must be str; got {type(target).__name__}: {target!r}"
                )
            self.update_wire(target, True)

        elif task_category == "pull_wire":
            if not isinstance(target, str):
                raise TypeError(
                    f"For task_category='pull_wire', target must be str; got {type(target).__name__}: {target!r}"
                )
            self.update_wire(target, False)

        elif task_category == "flip_switch":
            if not isinstance(target, str):
                raise TypeError(
                    f"For task_category='flip_switch', target must be str ('on'/'off'); got {type(target).__name__}: {target!r}"
                )
            task_lc = task_str.lower()
            switch_id = "top" if "top" in task_lc else "bottom"
            self.update_switch(switch_id, target == "on")

        elif task_category == "turn_knob":
            if not isinstance(target, int):
                raise TypeError(
                    f"For task_category='turn_knob', target must be int; got {type(target).__name__}: {target!r}"
                )
            self.update_knob(target)

        elif task_category in {"move_bb", "push_button"}:
            # No persistent box state to update.
            pass

        else:
            raise ValueError(f"Unknown task_category: {task_category!r}")

        return self.to_dict()

    def load_from_dict(self, state_dict):
        self.sliders = state_dict.get("sliders", self.sliders)
        self.wires_inserted = state_dict.get("wires_inserted", self.wires_inserted)
        self.switches = state_dict.get("switches", self.switches)
        self.knob_position = state_dict.get("knob_position", self.knob_position)

    def to_dict(self):
        # Return copies so callers can snapshot state without it mutating
        # as this BoxState instance continues to change.
        return {
            "sliders": dict(self.sliders),
            "wires_inserted": dict(self.wires_inserted),
            "switches": dict(self.switches),
            "knob_position": self.knob_position,
        }

    def __repr__(self):
        """
        Return a string representation of the BoxState.
        """
        inserted_wires = [color for color, inserted in self.wires_inserted.items() if inserted]
        return (
            f" - Set top slider to {self.sliders['top']},\n"
            f" - Set bottom slider to {self.sliders['bottom']},\n"
            f" - Insert wires {inserted_wires},\n"
            f" - Set top switch to {'ON' if self.switches['top'] else 'OFF'},\n"
            f" - Set bottom switch to {'ON' if self.switches['bottom'] else 'OFF'},\n"
            f" - Set knob position to {self.knob_position}"
        )

def parse_target(task: str, category: str):
    """Parse a task string into its target value.

    Examples:
        parse_target("Move the bottom slider to position 3.", "move_slider") -> 3
        parse_target("Move the box to the left", "move_bb") -> None
        parse_target("Pull the white wire", "pull_wire") -> "white"
        parse_target("Flip the top switch off with the left gripper", "flip_switch") -> "off"

    Returns:
        - int for position-based tasks (slider/knob)
        - str for color or switch-state tasks
        - None for tasks without a discrete target (move_bb)
    """

    task_norm = task.strip()
    if task_norm.endswith("."):
        task_norm = task_norm[:-1]
    task_lc = task_norm.lower()

    if category == "move_bb":
        return None

    if category in {"move_slider", "turn_knob"}:
        match = re.search(r"\bposition\s+(\d+)\b", task_lc)
        if not match:
            raise ValueError(f"Could not parse position from task={task!r} category={category!r}")
        return int(match.group(1))

    if category in {"pull_wire", "insert_wire"}:
        match = re.search(r"\b(black|blue|red|white)\b\s+wire\b", task_lc)
        if not match:
            raise ValueError(f"Could not parse wire color from task={task!r} category={category!r}")
        return match.group(1)

    if category == "push_button":
        match = re.search(r"\bpush\s+the\s+(blue|green|red|yellow)\b\s+button\b", task_lc)
        if not match:
            raise ValueError(f"Could not parse button color from task={task!r} category={category!r}")
        return match.group(1)

    if category == "flip_switch":
        match = re.search(r"\bswitch\s+(on|off)\b", task_lc)
        if not match:
            raise ValueError(f"Could not parse switch state from task={task!r} category={category!r}")
        return match.group(1)

    raise ValueError(f"Unknown category={category!r} for task={task!r}")

def sample_without_replacement(lst, n):
    """
    Sample n elements from lst without replacement.
    If the list runs out of elements, restart sampling from the full list.

    Args:
        lst: The list to sample from
        n: Number of samples to draw

    Returns:
        A list of n sampled elements
    """
    result = []
    pool = lst.copy()

    for _ in range(n):
        if not pool:
            pool = lst.copy()

        selected = random.choice(pool)
        result.append(selected)
        pool.remove(selected)

    return result

if __name__ == "__main__":
    seed = 37
    random.seed(seed)
    num_samples_per_task = 10
    # task_types = ["flip_switch", "insert_wire", "move_bb", "move_slider", "pull_wire", "push_button", "turn_knob"]
    task_types = ["flip_switch", "move_bb", "move_slider", "pull_wire", "push_button", "turn_knob"]
    initial_box_position = (
        " - Box centered and square relative to robot, \n"
        "    - 11 inches away from the center of the robot"
    )
    meta = {
        "seed": seed,
        "num_samples_per_task": num_samples_per_task,
        "task_types": task_types,
        "total_num_rollouts": num_samples_per_task * len(task_types),
        "initial_box_position": initial_box_position,
    }
    sampled_tasks = {
        task_types[0]: sample_without_replacement(flip_switch, num_samples_per_task),
        # task_types[1]: sample_without_replacement(insert_wire, num_samples_per_task),
        task_types[1]: sample_without_replacement(move_bb, num_samples_per_task),
        task_types[2]: sample_without_replacement(move_slider, num_samples_per_task),
        task_types[3]: sample_without_replacement(pull_wire, num_samples_per_task),
        task_types[4]: sample_without_replacement(push_button, num_samples_per_task),
        task_types[5]: sample_without_replacement(turn_knob, num_samples_per_task),
    }

    # add task category, target, and initial box state to each rollout
    box = BoxState()  # initialize the box to it's default state
    eval_rollouts = []
    for category, task_prompts in sampled_tasks.items():
        for i in range(len(task_prompts)):
            task_prompt = task_prompts[i]
            target = parse_target(task_prompt, category)
            box.randomize_box()  # randomize box state before generating initial state
            eval_rollouts.append({
                "task_prompt": task_prompt,
                "task_category": category,
                "target": target,
                "init_box_state": box.generate_valid_state({"task_prompt": task_prompt, "task_category": category, "target": target}),
            })

    # shuffle eval_rollouts
    random.shuffle(eval_rollouts)

    with open("eval_rollouts.json", "w") as f:
        import json
        json.dump({"meta": meta, "eval_rollouts": eval_rollouts}, f, indent=4)