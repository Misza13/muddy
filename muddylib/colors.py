BLACK = 0
RED = 1
GREEN = 2
YELLOW = 3
BLUE = 4
MAGENTA = 5
CYAN = 6
WHITE = 7

BRIGHT = 8

RESET = '\x1b[0m'

def color_seq(color):
    if color & BRIGHT:
        return f'\x1b[{(color & 7) + 30};1m'
    else:
        return f'\x1b[{(color & 7) + 30}m'

def colorify(text, color):
    return color_seq(color) + text + RESET