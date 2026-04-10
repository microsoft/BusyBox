import random
import json
import subprocess
import os

from robots.aloha.utils.sample_init_states import sample_init_state
from robots.aloha.utils.task_generator import (
    flip_switches,
    push_button,
    pull_wire,
    insert_wire,
    move_slider,
    turn_knob,
    move_box,
)

# Configuration constants
OPENPI_EXAMPLES_PATH = '/home/aloha/project_green/macgyver-demo/openpi/examples/aloha_real'
VENV_ACTIVATE = 'source .venv/bin/activate'
MAIN_SCRIPT = 'main.py'
OUTPUT_JSON_PATH = os.path.join(os.path.dirname(__file__), 'evaluation_results_rollouts.json')
TASK_TIMEOUT = 35  # seconds
SLEEP_COMMAND_PATH = "/home/aloha/interbotix_ws/src/aloha/scripts"
SLEEP_SCRIPT = "sleep.py"


def format_busybox_state(busybox_module_states, full_instruction):
    """Format busybox module states into a concise display format"""
    output = ""
    
    # Sliders section
    output += "----\n"
    for slider_name, value in busybox_module_states.get('sliders', {}).items():
        display_name = slider_name.replace('_', ' ')
        if isinstance(value, int):
            output += f"{display_name}: {value}\n"
        else:  # tuple for ranges
            output += f"{display_name}: between {value[0]} and {value[1]}\n"
    
    # Switches section
    output += "----\n"
    for switch_name, value in busybox_module_states.get('switches', {}).items():
        display_name = switch_name.replace('_', ' ')
        output += f"{display_name}: {value}\n"
    
    # Wires section
    output += "----\n"
    wire_colors = ['black', 'blue', 'red', 'white']
    wires = busybox_module_states.get('wires', {})
    for color in wire_colors:
        if color in wires:
            status = "short" if wires[color] == 'connected' else "open"
            output += f"{color} wire: {status}\n"
    
    # Knob section (extract from full instruction)
    output += "----\n"
    knob_line = [line for line in full_instruction.split('\n') if 'knob' in line.lower()]
    if knob_line:
        knob_info = knob_line[0].replace('- Set the knob ', '').replace('.', '')
        output += f"knob: {knob_info}\n"
    
    # Box and robot positioning (extract from full instruction)
    output += "----\n"
    lines = full_instruction.split('\n')
    
    # Box rotation
    box_rotation_lines = [line for line in lines if 'Rotate the BusyBox' in line]
    if box_rotation_lines:
        line = box_rotation_lines[0]
        if 'clockwise' in line:
            degrees = line.split(' degrees')[0].split('roughly ')[1]
            direction = 'CW' if 'clockwise' in line and 'counterclockwise' not in line else 'CCW'
            output += f"rotate BusyBox {degrees}° {direction}\n"
    else:
        # Check for "directly faces" positioning
        face_lines = [line for line in lines if 'BusyBox so that it directly faces' in line]
        if face_lines:
            output += "position BusyBox facing robot\n"
    
    # Box positioning
    position_lines = [line for line in lines if "Position the BusyBox ~4'' from the edge" in line]
    if position_lines:
        output += "position BusyBox 4\" from table edge\n"
        
    # Box displacement
    displacement_lines = [line for line in lines if 'Then move the BusyBox roughly' in line]
    if displacement_lines:
        line = displacement_lines[0]
        distance = line.split("roughly ")[1].split("''")[0]
        direction = "left" if "to the left" in line else "right"
        output += f"move BusyBox {distance}\" to {direction}\n"
    
    further_lines = [line for line in lines if 'Move the BusyBox roughly' in line and 'further' in line]
    if further_lines:
        line = further_lines[0]
        distance = line.split("roughly ")[1].split("''")[0]
        direction = "away" if "away from" in line else "closer"
        output += f"move BusyBox {distance}\" {direction}\n"
    
    # Robot rotation
    robot_rotation_lines = [line for line in lines if 'Rotate the robot roughly' in line]
    if robot_rotation_lines:
        line = robot_rotation_lines[0]
        degrees = line.split(' degrees')[0].split('roughly ')[1]
        direction = 'CW' if 'clockwise' in line and 'counterclockwise' not in line else 'CCW'
        output += f"rotate robot {degrees}° {direction}\n"
    else:
        # Check for "directly faces" positioning
        robot_face_lines = [line for line in lines if 'robot so that it directly faces' in line]
        if robot_face_lines:
            output += "position robot facing workspace\n"
    
    return output


def generate_evaluation_plan(seed=37, rollouts_per_task_type=10):
    random.seed(seed)
    evaluation_plan = []
    # For each task type, sample multiple rollouts
    task_types = {
        "FlipSwitch": flip_switches,
        "PushButton": push_button,
        "PullWire": pull_wire,
        "InsertWire": insert_wire,
        "MoveSlider": move_slider,
        "TurnKnob": turn_knob,
        "MoveBox": move_box,
    }
    for task_type, tasks in task_types.items():
        if len(tasks) == 0:
            continue
        for _ in range(rollouts_per_task_type):
            task = random.choice(tasks)
            init_state, busybox_module_states = sample_init_state(task['task_goal'], seed=random.randint(0, 1e6))
            evaluation_plan.append({
                "task_type": task_type,
                "task_instruction": task['task_instruction'],
                "initial_state": init_state,
                "busybox_module_states": busybox_module_states
            })
    return evaluation_plan


def run_sleep_script():
    """Move the robot to sleep position"""
    shell_cmd_cd = f"cd {SLEEP_COMMAND_PATH}"
    shell_cmd_run = f"python3 {SLEEP_SCRIPT}"
    shell_cmd = f"{shell_cmd_cd} && {shell_cmd_run}"
    try:
        subprocess.run(shell_cmd, shell=True, executable='/bin/bash', check=False)
    except Exception as e:
        print(f"Error running sleep script: {e}")


def run_inference_task(task_instruction):
    """Run the main inference script with the given task instruction"""
    shell_cmd_cd = f"cd {OPENPI_EXAMPLES_PATH}"
    shell_cmd_activate = f"{VENV_ACTIVATE}"
    shell_cmd_run = f"python3 {MAIN_SCRIPT} --args.prompt \"{task_instruction}\" --args.prompt-timeout {TASK_TIMEOUT}"
    shell_cmd = f"{shell_cmd_cd} && {shell_cmd_activate} && {shell_cmd_run}"
    try:
        subprocess.run(shell_cmd, shell=True, executable='/bin/bash', check=False)
    except Exception as e:
        print(f"Error running task '{task_instruction}': {e}")


if __name__ == "__main__":
    # Generate evaluation plan
    eval_plan = generate_evaluation_plan(seed=37, rollouts_per_task_type=10)
    
    # Tally system: {task_type: {'success': int, 'fail': int, 'total': int}}
    tally = {}
    notes = []
    index = 0

    # Initialize the output JSON file with empty tally and notes if it doesn't exist
    if not os.path.exists(OUTPUT_JSON_PATH):
        with open(OUTPUT_JSON_PATH, 'w') as f:
            json.dump({'tally': {}, 'notes': [], 'index': index}, f, indent=4)

    # Load existing data from the output JSON file
    with open(OUTPUT_JSON_PATH, 'r') as f:
        output_data = json.load(f)
    tally = output_data.get('tally', {})
    notes = output_data.get('notes', [])
    index = output_data.get('index', 0)
    
    # Check if all tasks are already evaluated
    if index >= len(eval_plan):
        print(f"All tasks already evaluated (index={index}, total={len(eval_plan)}). Nothing to do.")
        print("\nFinal tallies:")
        for task_type, stats in tally.items():
            print(f"{task_type}: {stats['success']} success, {stats['fail']} fail, {stats['total']} total")
        exit()
    
    print(f"Resuming evaluation at index {index} of {len(eval_plan)}")
    print(f"Total rollouts to evaluate: {len(eval_plan)}")
    
    # Main evaluation loop
    for i in range(index, len(eval_plan)):
        plan = eval_plan[i]
        task_type = plan['task_type']
        task_instruction = plan['task_instruction']
        
        # Initialize tally for this task type if not present
        if task_type not in tally:
            tally[task_type] = {'success': 0, 'fail': 0, 'total': 0}
        
        print("\n" + "=" * 80)
        print(f"Rollout {i+1}/{len(eval_plan)} - [{task_type}]: {task_instruction}")
        print("=" * 80)
        
        print("Before proceeding, please set the task's initial state as follows:")
        formatted_state = format_busybox_state(plan['busybox_module_states'], plan['initial_state'])
        print(formatted_state)
        
        user_choice = input("\nPress Enter to continue or 's' to skip this task: ").strip().lower()
        
        if user_choice == 's':
            print("Skipping this task...")
            # Update index to continue to next task
            index = i + 1
            with open(OUTPUT_JSON_PATH, 'w') as f:
                json.dump({'tally': tally, 'notes': notes, 'index': index}, f, indent=4)
            continue
        
        # Run the inference task
        print(f"Running inference for: {task_instruction}")
        run_inference_task(task_instruction)
        
        # Get user evaluation
        result = input(f"\nWas '{task_instruction}' successful? (y/n): ").strip().lower()
        if result == 'y':
            tally[task_type]['success'] += 1
            success = True
        else:
            tally[task_type]['fail'] += 1
            success = False
        tally[task_type]['total'] += 1

        note = input("Any notes about this task? (press Enter to skip): ").strip()
        notes.append({
            'task_type': task_type, 
            'task': task_instruction, 
            'success': success, 
            'note': note, 
            'index': i
        })

        # Print current tally for this task type
        print(f"Tally for {task_type}: {tally[task_type]['success']} success, {tally[task_type]['fail']} fail, {tally[task_type]['total']} total")

        # Update the JSON file after each task (increment index by 1)
        index = i + 1
        with open(OUTPUT_JSON_PATH, 'w') as f:
            json.dump({'tally': tally, 'notes': notes, 'index': index}, f, indent=4)
        
        # Optional sleep robot prompt
        sleep_robot = input("Move robot to sleep position? (y/n): ").strip().lower()
        if sleep_robot == 'y':
            print("Moving robot to sleep position...")
            run_sleep_script()

    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE!")
    print("=" * 80)
    print("\nFinal tallies:")
    for task_type, stats in tally.items():
        success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"{task_type}: {stats['success']}/{stats['total']} ({success_rate:.1f}% success)")
    
    total_success = sum(stats['success'] for stats in tally.values())
    total_tasks = sum(stats['total'] for stats in tally.values())
    overall_rate = (total_success / total_tasks * 100) if total_tasks > 0 else 0
    print(f"\nOverall: {total_success}/{total_tasks} ({overall_rate:.1f}% success)")
