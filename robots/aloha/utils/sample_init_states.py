import random
from robots.aloha.utils.control_values import *


CONTROLS2INIT_VALUES = {sfv + ' slider': SLIDER_EXACT_VALUES | SLIDER_INTERMDEDIATE_VALUES for sfv in SLIDER_FLAVOR_VALUES} \
    | {sfv + ' switch': SWITCH_VALUES for sfv in SWITCH_FLAVOR_VALUES} \
    | {wfv + ' wire': WIRE_VALUES for wfv in WIRE_FLAVOR_VALUES} \
    | {'knob': KNOB_EXACT_VALUES | KNOB_INTERMEDIATE_VALUES,
        'box rotation': BOX_ROTATION_VALUES,
        'box displacement_x': BOX_DISPLACEMENT_VALUES,
        'box displacement_y': BOX_DISPLACEMENT_VALUES,
        'robot rotation': ROBOT_ROTATION_VALUES}


def sample_init_state(controls2goal_values: dict, seed=None) -> tuple:
    """Sample an initial state description and return a tuple:
    (instruction_str, busybox_module_states)

    busybox_module_states has the structure:
    {
        'sliders': {'top_slider': ..., 'bottom_slider': ...},
        'switches': {'top_switch': ..., 'bottom_switch': ...},
        'wires': {'black': 'connected'|'disconnected', 'blue': 'connected'|'disconnected', ...}
    }
    """
    random.seed(seed if seed is not None else None)
    instruction = ''
    # initialize module state containers
    busybox_module_states = {
        'sliders': {},
        'switches': {},
        'wires': {}
    }
    wire_sampling_indicator = random.choice([0, 1])

    for control, values in CONTROLS2INIT_VALUES.items():   
        if control in controls2goal_values.keys():
            values = values - {controls2goal_values[control]}

        # NOTE: converting value sets to lists for sampling every time is very inefficient, but we can live with this, since our sets are so small...
        chosen_val = random.choice(list(values))

        split_control_name = control.split()
        if len(split_control_name) == 2 and split_control_name[1] == 'slider':
            instruction += f"- Set the {control} {f'to {chosen_val}' if type(chosen_val) == int else f'between {chosen_val[0]} and {chosen_val[1]}'}.\n"
            # map to busybox sliders
            slider_name = f"{split_control_name[0]}_slider"
            busybox_module_states['sliders'][slider_name] = chosen_val
        elif len(split_control_name) == 2 and split_control_name[1] == 'switch':
            instruction += f"- Set the {control} {'to off' if chosen_val == 0 else 'to on'}.\n"
            switch_name = f"{split_control_name[0]}_switch"
            busybox_module_states['switches'][switch_name] = ('on' if chosen_val == 1 else 'off')
        elif len(split_control_name) == 1 and split_control_name[0] == 'knob':
            instruction += f"- Set the {control} {f'to {chosen_val}' if type(chosen_val) == int else f'between {chosen_val[0]} and {chosen_val[1]}'}.\n"
        elif len(split_control_name) == 2 and split_control_name[1] == 'wire':
            # With p = 1/2, leave all the wires plugged in
            if wire_sampling_indicator == 1 and control not in controls2goal_values.keys():
                instruction += f"- Plug in both ends of the {control} into the terminals of that same color.\n"
                busybox_module_states['wires'][split_control_name[0]] = 'connected'
            else:
                if chosen_val == 1:
                    instruction += f"- Plug in both ends of the {control} into the terminals of that same color.\n"
                    busybox_module_states['wires'][split_control_name[0]] = 'connected'
                else:
                    instruction += f"- Plug in one end of the {control} but leave the other one unplugged.\n"
                    busybox_module_states['wires'][split_control_name[0]] = 'disconnected'
        elif control == 'robot rotation':
            if chosen_val != 0:
                instruction += f"- Rotate the robot roughly {abs(chosen_val)} degrees {'clockwise' if chosen_val > 0 else 'counterclockwise'} from its neutral position.\n"
            else:
                instruction += f"- Position the robot so that it directly faces the workspace.\n"
        elif control == 'box rotation':
            if chosen_val != 0:
                instruction += f"- Rotate the BusyBox roughly {abs(chosen_val)} degrees {'clockwise' if chosen_val > 0 else 'counterclockwise'} from its neutral position.\n"
            else:
                instruction += f"- Position the BusyBox so that it directly faces the robot.\n"
        elif control == 'box displacement_x':
            instruction += f"- Position the BusyBox ~4'' from the edge of the table nearest to Aloha, centered along that edge.\n"
            if chosen_val != 0:
                dir = random.choice(["to the left", "to the right"])
                instruction += f"  Then move the BusyBox roughly {abs(chosen_val)}'' {dir}.\n"
                #instruction += f"  Then move the BusyBox roughly {abs(chosen_val)}'' to the {'right' if chosen_val > 0 else 'left'}.\n"
            
            """
            if chosen_val != 0:
                instruction += f"- Move the BusyBox roughly {abs(chosen_val)} cm {'right' if chosen_val > 0 else 'left'} from the center of the workspace.\n"
            else:
                instruction += f"- Position the BusyBox in the middle between the left and the right edges of the workspace.\n"
            """
        elif control == 'box displacement_y':
            if chosen_val != 0:
                instruction += f"- Move the BusyBox roughly {abs(chosen_val)}'' further {'away from' if chosen_val > 0 else 'closer to'} the robot.\n"
            """
            if chosen_val != 0:
                instruction += f"- Move the BusyBox roughly {abs(chosen_val)} cm {'away from' if chosen_val > 0 else 'closer to'} the robot from the center of the workspace.\n"
            else:
                instruction += f"- Position the BusyBox in the middle between the near and the far edges of the workspace.\n"
            """
        else:
            raise ValueError(f'Unknown control: {control}')
        
    instruction += f"- Randomize the starting pose of the arms before you start recording the trajectory.\n"

    return instruction, busybox_module_states


if __name__ == '__main__':
    from robots.aloha.utils.task_generator import generate_tasks
    tasks = generate_tasks()
    print(f"Generated {len(tasks)} tasks: ")
    # sample_init_state()

    task = random.choice(tasks)
    print(f"Sampled task: {task}")
    instruction, busybox_module_states = sample_init_state(task['task_goal'])
    print(f"Sampled init state:\n{instruction}")
    print("BusyBox module states:")
    import pprint
    pprint.pprint(busybox_module_states)

    print(f"top_slider type: {type(busybox_module_states['sliders']['top_slider'])}")
    print(f"bottom_slider type: {type(busybox_module_states['sliders']['bottom_slider'])}")
