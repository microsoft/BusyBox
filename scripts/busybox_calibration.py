import time

from robots.aloha.utils.busybox_listener import BusyBoxListener

from robots.aloha.utils.config import COLLECTION_CONFIG
from robots.aloha.utils.config import MQTT_SUBSCRIBE_TOPICS, EINK_PUBLISH_TOPIC


def calibrate_buttons(button_layout, busybox_listener, bb_DT):
    for button_name in button_layout:
        time.sleep(0.2)
        busybox_listener.publish_eink(f"1:Press {button_name.replace('_', ' ').title()}")
        time.sleep(0.2)
        busybox_listener.publish_eink("2:")
        time.sleep(1.0)  # wait a bit before next button
        waiting_for_button = True
        while waiting_for_button:
            latest = busybox_listener.latest_state()
            # Guard against None or unexpected formats from latest_state()
            if not latest:
                time.sleep(bb_DT)
                continue

            buttons = latest.get('buttons') if isinstance(latest, dict) else None
            if not buttons:
                # Data is present but doesn't include buttons; wait for next update
                print("Received state without 'buttons' key; waiting...")
                time.sleep(bb_DT)
                continue

            values = buttons.get('values') if isinstance(buttons, dict) else None
            if not isinstance(values, (list, tuple)):
                print("'buttons.values' missing or malformed; waiting...")
                time.sleep(bb_DT)
                continue

            pressed = [i for i, v in enumerate(values) if v == 0]  # 0 == pressed
            if len(pressed) == 1:
                button_layout[button_name]["index"] = pressed[0]
                print(f"{button_name.replace('_', ' ').title()} index: {pressed[0]}")
                busybox_listener.publish_eink(f"2:{button_name.title()} idx: {pressed[0]}")
                waiting_for_button = False
            elif len(pressed) > 1:
                print("Multiple buttons pressed. Press only one button.")
                busybox_listener.publish_eink("2:Only one Btn")
            time.sleep(bb_DT)
    return button_layout

def calibrate_switches(switch_layout, busybox_listener, bb_DT):
    for switch_name in switch_layout:
        for state in ("On", "Off"):
            time.sleep(0.2)
            busybox_listener.publish_eink(f"1:Flip {switch_name.replace('_', ' ').title()} {state}")
            time.sleep(0.2)
            busybox_listener.publish_eink("2:Red Btn confirm")
            time.sleep(0.2)
            waiting_for_button = True
            while waiting_for_button:
                latest = busybox_listener.latest_state()
                # Guard against None or unexpected formats from latest_state()
                if not latest:
                    time.sleep(bb_DT)
                    continue

                # First: wait for user confirmation via the red button press
                buttons = latest.get('buttons') if isinstance(latest, dict) else None
                if not buttons:
                    print("Waiting for red button press (no 'buttons' key yet)...")
                    time.sleep(bb_DT)
                    continue

                b_values = buttons.get('values') if isinstance(buttons, dict) else None
                if not isinstance(b_values, (list, tuple)):
                    print("'buttons.values' missing or malformed; waiting for red button press...")
                    time.sleep(bb_DT)
                    continue

                # Ensure we know the red button index from earlier calibration
                red_info = button_layout.get('red_button', {})
                red_idx = red_info.get('index')
                red_pressed_state = red_info.get('pressed_state', 0)
                if red_idx is None or not (0 <= red_idx < len(b_values)):
                    print("Red button not calibrated or index out of range; please calibrate buttons first.")
                    time.sleep(bb_DT)
                    continue

                # Only proceed to read switch state after the red button is pressed
                if b_values[red_idx] != red_pressed_state:
                    # still waiting for confirmation press
                    time.sleep(bb_DT)
                    continue

                # Confirmation received — now inspect switches
                switches = latest.get('switches') if isinstance(latest, dict) else None
                if not switches:
                    # Data is present but doesn't include switches; wait for next update
                    print("Received state without 'switches' key; waiting...")
                    time.sleep(bb_DT)
                    continue

                values = switches.get('values') if isinstance(switches, dict) else None
                if not isinstance(values, (list, tuple)):
                    print("'switches.values' missing or malformed; waiting...")
                    time.sleep(bb_DT)
                    continue

                if switch_layout[switch_name]["index"] is None:
                    # Need to determine index first
                    possible_indices = [
                        i for i in range(len(values))
                        if i not in [s["index"] for s in switch_layout.values() if s["index"] is not None]
                    ]
                else:
                    possible_indices = [switch_layout[switch_name]["index"]]

                for idx in possible_indices:
                    current_value = values[idx]
                    if state == "On" and current_value == 1:
                        switch_layout[switch_name]["index"] = idx
                        switch_layout[switch_name]["on_state"] = current_value
                        print(f"{switch_name.replace('_', ' ').title()} index: {idx} ON state: {current_value}")
                        busybox_listener.publish_eink(f"2:{switch_name.title()} idx:{idx} ON")
                        waiting_for_button = False
                        break
                    elif state == "Off" and current_value == 0:
                        switch_layout[switch_name]["index"] = idx
                        switch_layout[switch_name]["off_state"] = current_value
                        print(f"{switch_name.replace('_', ' ').title()} index: {idx} OFF state: {current_value}")
                        busybox_listener.publish_eink(f"2:{switch_name.title()} idx:{idx} OFF")
                        waiting_for_button = False
                        break

                if len(possible_indices) > 1 and waiting_for_button:
                    print("Multiple switches could match. Ensure only the target switch is flipped.")
                    busybox_listener.publish_eink("2:Only one Switch should be flipped at a time.")
                time.sleep(bb_DT)
    return switch_layout


def calibrate_wires(wire_layout, busybox_listener, bb_DT):
    # Ask user to start with all wires unplugged
    time.sleep(0.2)
    busybox_listener.publish_eink("1:Unplug all wires")
    time.sleep(0.2)

    # Wait for initial red button press to confirm starting wire calibration
    waiting_for_red_start = True
    while waiting_for_red_start:
        latest = busybox_listener.latest_state()
        if not latest:
            time.sleep(bb_DT)
            continue

        buttons = latest.get('buttons') if isinstance(latest, dict) else None
        if not buttons:
            time.sleep(bb_DT)
            continue

        b_values = buttons.get('values') if isinstance(buttons, dict) else None
        if not isinstance(b_values, (list, tuple)):
            time.sleep(bb_DT)
            continue

        red_info = button_layout.get('red_button', {})
        red_idx = red_info.get('index')
        red_pressed_state = red_info.get('pressed_state', 0)

        if red_idx is None or not (0 <= red_idx < len(b_values)):
            print("Waiting for calibrated red button index...")
            time.sleep(bb_DT)
            continue

        if b_values[red_idx] == red_pressed_state:
            busybox_listener.publish_eink("2:Start Cal")
            ## Note the unplugged state of all the wires ##
            waiting_for_red_start = False
        time.sleep(bb_DT)

    for wire_name in wire_layout:
        busybox_listener.publish_eink(f"1:Insert {wire_name.replace('_', ' ').title()}")
        time.sleep(0.2)
        busybox_listener.publish_eink("2:Press Red to confirm")
        time.sleep(0.2)

        waiting_for_confirmation = True
        while waiting_for_confirmation:
            latest = busybox_listener.latest_state()
            # Basic guards
            if not latest:
                time.sleep(bb_DT)
                continue

            # Wait for red button press (confirmation)
            buttons = latest.get('buttons') if isinstance(latest, dict) else None
            if not buttons:
                print("Waiting for red button press (no 'buttons' key yet)...")
                time.sleep(bb_DT)
                continue

            b_values = buttons.get('values') if isinstance(buttons, dict) else None
            if not isinstance(b_values, (list, tuple)):
                print("'buttons.values' missing or malformed; waiting for red button press...")
                time.sleep(bb_DT)
                continue

            # Check red button calibration
            red_info = button_layout.get('red_button', {})
            red_idx = red_info.get('index')
            red_pressed_state = red_info.get('pressed_state', 0)
            if red_idx is None or not (0 <= red_idx < len(b_values)):
                print("Red button not calibrated or index out of range; please calibrate buttons first.")
                time.sleep(bb_DT)
                continue

            # Proceed only when red button is pressed
            if b_values[red_idx] != red_pressed_state:
                time.sleep(bb_DT)
                continue

            # Confirmation received; read wires
            wires = latest.get('wires') if isinstance(latest, dict) else None
            if not wires:
                print("Received state without 'wires' key; waiting...")
                time.sleep(bb_DT)
                continue

            values = wires.get('values') if isinstance(wires, dict) else None
            if not isinstance(values, (list, tuple)):
                print("'wires.values' missing or malformed; waiting...")
                time.sleep(bb_DT)
                continue

            # Determine which index changed from unplugged (assume unplugged state is 0 or None)
            # We assume user started with all unplugged and now inserted exactly one wire.
            inserted_indices = [i for i, v in enumerate(values) if v != 0]
            if len(inserted_indices) == 1:
                idx = inserted_indices[0]
                wire_layout[wire_name]['index'] = idx
                wire_layout[wire_name]['inserted_state'] = values[idx]
                print(f"{wire_name.replace('_', ' ').title()} index: {idx} inserted state: {values[idx]}")
                busybox_listener.publish_eink(f"2:{wire_name.title()} idx:{idx} OK")
                waiting_for_confirmation = False
            elif len(inserted_indices) > 1:
                print("Multiple wires appear inserted. Ensure only the target wire is inserted.")
                busybox_listener.publish_eink("2:Only one Wire")
            else:
                # No wire detected as inserted (maybe insertion reports 0 for inserted) — try alternative detection
                # Look for any change from previous known states or non-zero truthy values
                possible = [i for i, v in enumerate(values) if bool(v)]
                if len(possible) == 1:
                    idx = possible[0]
                    wire_layout[wire_name]['index'] = idx
                    wire_layout[wire_name]['inserted_state'] = values[idx]
                    print(f"{wire_name.replace('_', ' ').title()} index: {idx} inserted state: {values[idx]}")
                    busybox_listener.publish_eink(f"2:{wire_name.title()} idx:{idx} OK")
                    waiting_for_confirmation = False
                else:
                    print("No single inserted wire detected yet; waiting for correct insertion and Red press.")
            time.sleep(bb_DT)

    return wire_layout


if __name__ == "__main__":
    bb_freq = 50  # Hz
    bb_DT = 1.0 / bb_freq

    busybox_listener = BusyBoxListener(
        broker=COLLECTION_CONFIG['MQTT_broker'],
        port=COLLECTION_CONFIG['MQTT_port'],
        topics=MQTT_SUBSCRIBE_TOPICS,
        e_ink_topic=EINK_PUBLISH_TOPIC
    )
    busybox_listener.start()

    # Calibrate buttons
    print("Calibrating buttons...")

    button_layout = {
        "red_button": {
            "index": None,  # to be filled in
            "pressed_state": 0
        },
        "blue_button": {
            "index": None,
            "pressed_state": 0
        },
        "green_button": {
            "index": None,
            "pressed_state": 0
        },
        "yellow_button": {
            "index": None,
            "pressed_state": 0
        },
    }

    button_layout = calibrate_buttons(button_layout, busybox_listener, bb_DT)
    print(f"Button calibration complete:{button_layout}")
    

    # loop forever and output the latest state everytime the red button is pressed
    while True:
        latest = busybox_listener.latest_state()
        if not latest:
            time.sleep(bb_DT)
            continue

        buttons = latest.get('buttons') if isinstance(latest, dict) else None
        if not buttons:
            time.sleep(bb_DT)
            continue

        b_values = buttons.get('values') if isinstance(buttons, dict) else None
        if not isinstance(b_values, (list, tuple)):
            time.sleep(bb_DT)
            continue

        red_info = button_layout.get('red_button', {})
        red_idx = red_info.get('index')
        red_pressed_state = red_info.get('pressed_state', 0)

        if red_idx is None or not (0 <= red_idx < len(b_values)):
            print("Waiting for calibrated red button index...")
            time.sleep(bb_DT)
            continue

        if b_values[red_idx] == red_pressed_state:
            print(f"Red button pressed. Latest BusyBox state:\n{latest}")
            busybox_listener.publish_eink("2:State printed in console")
            time.sleep(1.0)  # debounce delay

