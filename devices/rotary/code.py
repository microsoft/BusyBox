import rotaryio
import board
import time

encoder = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)


original_position = encoder.position
color = 0  # start at red
while True:

    position = encoder.position - original_position
    print(f"Rotary: {position}")
    time.sleep(0.1)
