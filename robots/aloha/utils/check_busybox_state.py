import json
from pathlib import Path
from time import sleep

# from robots.aloha.record_busybox_episodes import check_busybox_state
from robots.aloha.utils.busybox_listener import BusyBoxListener

from robots.aloha.utils.config import COLLECTION_CONFIG, MQTT_SUBSCRIBE_TOPICS

BUSYBOX_DIGITAL_MAPPING_PATH = Path("/home/aloha/BusyBox/robots/busybox_digital_mapping.json")
with BUSYBOX_DIGITAL_MAPPING_PATH.open("r") as f:
    BUSYBOX_DIGITAL_MAPPING: dict = json.load(f)

def check_busybox_state(busybox_listener: BusyBoxListener, target_busybox_state, debug: bool = False) -> bool:
    latest_busybox_state = busybox_listener.latest_state()

    sliders_correct = False
    switches_correct = False
    wires_correct = False
    
    # check sliders
    top_slider_idx = BUSYBOX_DIGITAL_MAPPING["sliders"]["top_slider"]["index"]
    top_slider_map = BUSYBOX_DIGITAL_MAPPING["sliders"]["top_slider"]["mapping"]
    top_slider_pos = latest_busybox_state["sliders"]["values"][top_slider_idx]
    bottom_slider_idx = BUSYBOX_DIGITAL_MAPPING["sliders"]["bottom_slider"]["index"]
    bottom_slider_map = BUSYBOX_DIGITAL_MAPPING["sliders"]["bottom_slider"]["mapping"]
    bottom_slider_pos = latest_busybox_state["sliders"]["values"][bottom_slider_idx]
    
    target_top_slider = target_busybox_state["sliders"]["top_slider"]
    target_bottom_slider = target_busybox_state["sliders"]["bottom_slider"]
    
    slider_correctness = [False, False]  # [top_slider_reading, bottom_slider_reading]
    i = 0
    for slider_pos, target_pos, slider_map in [
        (top_slider_pos, target_top_slider, top_slider_map),
        (bottom_slider_pos, target_bottom_slider, bottom_slider_map),
    ]:
        if type(target_pos) is int:
            # find the closes value in the mapping
            slider_min_diff = 10e10  # large number
            slider_reading = None  # reading on the box [1:5] inclusive
            for slider_key, slider_val in slider_map.items():
                slider_diff = abs(slider_val - slider_pos)
                if slider_diff < slider_min_diff:
                    slider_min_diff = slider_diff
                    slider_reading = slider_key
            if slider_reading == str(target_pos):
                slider_correctness[i] = True
            elif debug:
                slider_designation = "top" if i == 0 else "bottom"
                print(f"Slider {slider_designation} incorrect: reading {slider_reading}, target {target_pos}")
        if type(target_pos) is tuple:
            upper_bound, lower_bound = target_pos
            lower_bound_value = slider_map[str(lower_bound)]
            upper_bound_value = slider_map[str(upper_bound)]
            if lower_bound_value <= slider_pos <= upper_bound_value:
                slider_correctness[i] = True
            elif debug:
                slider_designation = "top" if i == 0 else "bottom"
                print(f"Slider {slider_designation} incorrect: reading {slider_pos}, target between {lower_bound_value} and {upper_bound_value}")
        i += 1
    if all(slider_correctness):
        sliders_correct = True

    # check switches
    top_switch_idx = BUSYBOX_DIGITAL_MAPPING["switches"]["top_switch"]["index"]
    bottom_switch_idx = BUSYBOX_DIGITAL_MAPPING["switches"]["bottom_switch"]["index"]
    top_switch_pos = latest_busybox_state["switches"]["values"][top_switch_idx]
    bottom_switch_pos = latest_busybox_state["switches"]["values"][bottom_switch_idx]

    target_top_switch = target_busybox_state["switches"]["top_switch"]
    if target_top_switch == 'on':
        target_mapping = BUSYBOX_DIGITAL_MAPPING["switches"]["top_switch"]["on_value"] 
    else:
        target_mapping = BUSYBOX_DIGITAL_MAPPING["switches"]["top_switch"]["off_value"]
    target_bottom_switch = target_busybox_state["switches"]["bottom_switch"]
    if target_bottom_switch == 'on':
        target_mapping_bottom = BUSYBOX_DIGITAL_MAPPING["switches"]["bottom_switch"]["on_value"] 
    else:
        target_mapping_bottom = BUSYBOX_DIGITAL_MAPPING["switches"]["bottom_switch"]["off_value"]
    switch_correctness = [False, False]  # [top_switch_reading, bottom_switch_reading]

    if top_switch_pos == target_mapping:
        switch_correctness[0] = True
    elif debug:
        print(f"Top switch incorrect: reading {top_switch_pos}, target {target_mapping}")
    if bottom_switch_pos == target_mapping_bottom:
        switch_correctness[1] = True
    elif debug:
        print(f"Bottom switch incorrect: reading {bottom_switch_pos}, target {target_mapping_bottom}")

    if all(switch_correctness):
        switches_correct = True

    # check wires
    black_wire_idx = BUSYBOX_DIGITAL_MAPPING["wires"]["black_wire"]["index"]
    blue_wire_idx = BUSYBOX_DIGITAL_MAPPING["wires"]["blue_wire"]["index"]
    red_wire_idx = BUSYBOX_DIGITAL_MAPPING["wires"]["red_wire"]["index"]
    white_wire_idx = BUSYBOX_DIGITAL_MAPPING["wires"]["white_wire"]["index"]
    black_wire_pos = latest_busybox_state["wires"]["values"][black_wire_idx]
    blue_wire_pos = latest_busybox_state["wires"]["values"][blue_wire_idx]
    red_wire_pos = latest_busybox_state["wires"]["values"][red_wire_idx]
    white_wire_pos = latest_busybox_state["wires"]["values"][white_wire_idx]

    target_black_wire = target_busybox_state["wires"]["black"]
    if target_black_wire == 'connected':
        target_black_mapping = BUSYBOX_DIGITAL_MAPPING["wires"]["black_wire"]["connected_value"]
    else:
        target_black_mapping = BUSYBOX_DIGITAL_MAPPING["wires"]["black_wire"]["disconnected_value"]
    target_blue_wire = target_busybox_state["wires"]["blue"]
    if target_blue_wire == 'connected':
        target_blue_mapping = BUSYBOX_DIGITAL_MAPPING["wires"]["blue_wire"]["connected_value"]
    else:
        target_blue_mapping = BUSYBOX_DIGITAL_MAPPING["wires"]["blue_wire"]["disconnected_value"]
    target_red_wire = target_busybox_state["wires"]["red"]
    if target_red_wire == 'connected':
        target_red_mapping = BUSYBOX_DIGITAL_MAPPING["wires"]["red_wire"]["connected_value"]
    else:
        target_red_mapping = BUSYBOX_DIGITAL_MAPPING["wires"]["red_wire"]["disconnected_value"]
    target_white_wire = target_busybox_state["wires"]["white"]
    if target_white_wire == 'connected':
        target_white_mapping = BUSYBOX_DIGITAL_MAPPING["wires"]["white_wire"]["connected_value"]
    else:
        target_white_mapping = BUSYBOX_DIGITAL_MAPPING["wires"]["white_wire"]["disconnected_value"]

    wire_correctness = [False, False, False, False]  # [black_wire, blue_wire, red_wire, white_wire]
    if black_wire_pos == target_black_mapping:
        wire_correctness[0] = True
    elif debug:
        print(f"Black wire incorrect: reading {black_wire_pos}, target {target_black_mapping}")
    if blue_wire_pos == target_blue_mapping:
        wire_correctness[1] = True
    elif debug:
        print(f"Blue wire incorrect: reading {blue_wire_pos}, target {target_blue_mapping}")
    if red_wire_pos == target_red_mapping:
        wire_correctness[2] = True
    elif debug:
        print(f"Red wire incorrect: reading {red_wire_pos}, target {target_red_mapping}")
    if white_wire_pos == target_white_mapping:
        wire_correctness[3] = True
    elif debug:
        print(f"White wire incorrect: reading {white_wire_pos}, target {target_white_mapping}")
    
    if all(wire_correctness):
        wires_correct = True

    busybox_in_correct_state = sliders_correct and switches_correct and wires_correct
    return busybox_in_correct_state, (slider_correctness, switches_correct, wires_correct)


if __name__ == '__main__':
    BUSYBOX_DIGITAL_MAPPING_PATH = Path("/home/aloha/BusyBox/robots/busybox_digital_mapping.json")
    with BUSYBOX_DIGITAL_MAPPING_PATH.open("r") as f:
        BUSYBOX_DIGITAL_MAPPING: dict = json.load(f)

    busybox_listener = BusyBoxListener(
        broker=COLLECTION_CONFIG['MQTT_broker'],
        port=COLLECTION_CONFIG['MQTT_port'],
        topics=MQTT_SUBSCRIBE_TOPICS,
    )
    busybox_listener.start()
    
    target_busybox_state = {
        'sliders': {
            'bottom_slider': 1,
            'top_slider': (1, 2),
        },
        'switches': {
            'bottom_switch': 'on',
            'top_switch': 'off',
        },
        'wires': {
            'black': 'disconnected',
            'blue': 'disconnected',
            'red': 'connected',
            'white': 'disconnected',
        },
    }
    while True:
        is_compliant = check_busybox_state(busybox_listener, target_busybox_state)
        print(f"Is compliant? {is_compliant}")
        # print("Latest state:")
        # print(json.dumps(busybox_listener.latest_state(), indent=2))
        sleep(1.0)
