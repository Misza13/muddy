import curses

from muddylib.windows import BufferedTextWindow, InputWindow


class MudScreen(object):
    def __init__(self, screen):
        self.screen = screen
        self.screen.keypad(True)
        self.screen.scrollok(False)
        
        y, x = screen.getmaxyx()
        x_split = x * 2 // 3

        self.main_window = BufferedTextWindow('MainWindow')
        self.chat_window = BufferedTextWindow('ChatWindow')

        self.input = InputWindow('InputWindow')
        
        self.windows = [
            self.main_window,
            self.chat_window,
            self.input
            ]

    def refresh_all(self):
        self.screen.clear()

        y, x = self.screen.getmaxyx()
        x = x-1 #Issue with curses - last column is not really supported
        x_split = x * 2 // 3

        self.main_window.resize(y-4, x_split-1, 1, 1)
        self.chat_window.resize(y-4, x-x_split-2, 1, x_split+1)
        self.input.resize(x-2, y-2, 1)
        
        pmap = PixMap(y, x)
        for win in self.windows:
            pmap.paint_window(win.lines, win.columns, win.y, win.x)
        
        for yy in range(y):
            for xx in range(x):
                if pmap.get_state(yy, xx):
                    try:
                        self.screen.addch(yy, xx, adjacency_to_char(pmap.get_adjacency(yy, xx)))
                    except:
                        #This empty catch is a curses workaround
                        pass

        self.screen.refresh()

        for win in self.windows:
            win.redraw()


class PixMap:
    def __init__(self, lines, columns):
        self.lines = lines
        self.columns = columns
        
        self._bitmap = [[True for c in range(columns)] for r in range(lines)]
    
    def paint_window(self, lines, columns, y, x):
        for r in range(y, y + lines):
            for c in range(x, x + columns):
                self._bitmap[r][c] = False
    
    def get_state(self, y, x):
        if x < 0 or x >= self.columns or y < 0 or y >= self.lines:
            return False
        
        return self._bitmap[y][x]
    
    def get_adjacency(self, y, x):
        """
            +---+
            | 1 |
        +---+---+---+
        | 8 | * | 2 |
        +---+---+---+
            | 4 |
            +---+
        """
        return 1 * self.get_state(y-1, x) +\
               2 * self.get_state(y, x+1) +\
               4 * self.get_state(y+1, x) +\
               8 * self.get_state(y, x-1)

def adjacency_to_char(adj):
    if adj == 1 or adj == 4 or adj == 1+4:
        return curses.ACS_VLINE
    elif adj == 2 or adj == 8 or adj == 2+8:
        return curses.ACS_HLINE
    elif adj == 1+2:
        return curses.ACS_LLCORNER
    elif adj == 2+4:
        return curses.ACS_ULCORNER
    elif adj == 4+8:
        return curses.ACS_URCORNER
    elif adj == 8+1:
        return curses.ACS_LRCORNER
    elif adj == 1+2+4:
        return curses.ACS_LTEE
    elif adj == 2+4+8:
        return curses.ACS_TTEE
    elif adj == 4+8+1:
        return curses.ACS_RTEE
    elif adj == 8+1+2:
        return curses.ACS_BTEE
    elif adj == 1+2+4+8:
        return curses.ACS_PLUS
    else:
        return '#'