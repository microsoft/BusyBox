import time
import board
from analogio import AnalogIn
import adafruit_dotstar
from digitalio import DigitalInOut, Direction, Pull


black = DigitalInOut(board.D0)
red = DigitalInOut(board.D1)
green = DigitalInOut(board.D2)
white = DigitalInOut(board.D3)


black.direction = Direction.INPUT
red.direction = Direction.INPUT
green.direction = Direction.INPUT
white.direction = Direction.INPUT


while True:
    values = {
        "black": 0,
        "red": 0,
        "green": 0,
        "white": 0,
    }
    gather_range = 10
    for i in range(gather_range):
        values["black"] += black.value
        values["red"] += red.value
        values["green"] += green.value
        values["white"] += white.value
        time.sleep(0.01)

    values["black"] /= gather_range
    values["red"] /= gather_range
    values["green"] /= gather_range
    values["white"] /= gather_range

    for key, value in values.items():
        if value > 0.1:
            values[key] = 1
        else:
            values[key] = 0
    print("WIRES: ", values)

    time.sleep(0.1)
