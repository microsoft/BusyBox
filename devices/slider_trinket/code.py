import time
import board
from analogio import AnalogIn
import adafruit_dotstar
from digitalio import DigitalInOut, Direction, Pull

# Initialize the single onboard DotStar LED
pixels = adafruit_dotstar.DotStar(
    board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, 1, brightness=0.5
)

# Initialize the potentiometer input
potentiometer1 = AnalogIn(board.D1)
potentiometer2 = AnalogIn(board.D2)


# For Gemma M0, Trinket M0, Metro M0 Express, ItsyBitsy M0 Express, Itsy M4 Express, QT Py M0
# switch = DigitalInOut(board.D2)
# switch.direction = Direction.Input
# switch.pull = Pull.UP


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


while True:
    # Read the potentiometer value

    pot_value1 = 0
    pot_value2 = 0
    gather_range = 10
    for i in range(gather_range):
        pot_value1 += get_voltage(potentiometer1)
        pot_value2 += get_voltage(potentiometer2)

    pot_value1 /= gather_range
    pot_value2 /= gather_range

    # Scale the potentiometer value to fit the 0-5 range
    scaled_value1 = 5 - (5 * (pot_value1 - 0.3) / (3.0))
    scaled_value2 = 5 - (5 * (pot_value2 - 0.3) / (2.7))

    # Print the potentiometer value and RGB values for debugging
    print(
        f"SLIDER 1: {pot_value1:.2f} V, Scaled Value: {scaled_value1:.2f}\t"
        + f"SLIDER 2: {pot_value2:.2f} V, Scaled Value: {scaled_value2:.2f}"
    )

    time.sleep(0.1)
