BLACK = 0
RED = 1
GREEN = 2
YELLOW = 3
BLUE = 4
MAGENTA = 5
CYAN = 6
WHITE = 7

BRIGHT = 8

def colorify(text, color):
    if color & BRIGHT:
        ansi_color = f'\x1b[{(color & 7) + 30};1m'
    else:
        ansi_color = f'\x1b[{(color & 7) + 30}m'
    
    return ansi_color + text + '\x1b[0m'