import curses

from muddylib.windows import BufferedTextWindow, InputWindow, LayoutElement


class MudScreen(object):
    def __init__(self, screen, screen_config):
        self.screen = screen
        self.screen.keypad(True)
        self.screen.scrollok(False)
        
        maker = LayoutMaker()
        root, windows = maker.make_from(screen_config['root'])
        self.root = root
        self.windows = windows

    def refresh_all(self):
        self.screen.clear()

        y, x = self.screen.getmaxyx()
        x = x-1 #Issue with curses - last column is not really supported
        
        self.root.resize(y, x, 0, 0)
        
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


class AbstractStackLayout(LayoutElement):
    def __init__(self):
        super(AbstractStackLayout, self).__init__()
        
        self.elements = []
        self.layouts = []

    def init_from_config(self, config):
        self.layouts = config['layouts']
        self.elements = []

        maker = LayoutMaker()
        windows = []

        for elem in config['elements']:
            child, child_windows = maker.make_from(elem)
            self.elements.append(child)
            windows.extend(child_windows)

        return windows
        
    def add_child(self, element, layout):
        self.elements.append(element)
        self.layouts.append(layout)


class VerticalStackLayout(AbstractStackLayout):
    def resize(self, lines, columns, y, x):
        super(VerticalStackLayout, self).resize(lines, columns, y, x)
        
        actuals = [element.lines for element in self.elements]
        new_lines = compute_layout(lines, self.layouts, actuals)
        new_ys = cumsum_w_borders(new_lines)
        
        for e, element in enumerate(self.elements):
            if type(element) in [VerticalStackLayout, HorizontalStackLayout]:
                element.resize(new_lines[e]+2, columns, new_ys[e]-1, x)
            else:
                element.resize(new_lines[e], columns-2, new_ys[e], x+1)
    

class HorizontalStackLayout(AbstractStackLayout):
    def resize(self, lines, columns, y, x):
        super(HorizontalStackLayout, self).resize(lines, columns, y, x)
        
        actuals = [element.columns for element in self.elements]
        new_columns = compute_layout(columns, self.layouts, actuals)
        new_xs = cumsum_w_borders(new_columns)
        
        for e, element in enumerate(self.elements):
            if type(element) in [VerticalStackLayout, HorizontalStackLayout]:
                element.resize(lines, new_columns[e]+2, y, new_xs[e]-1)
            else:
                element.resize(lines-2, new_columns[e], y+1, new_xs[e])


def compute_layout(total, layouts, actuals):
    unallocated = total - 1 #For border
    new_lines = list(range(len(layouts)))
    
    total_props = 0
    
    for l, layout in enumerate(layouts):
        unallocated -= 1 #For border
        
        if layout.isnumeric():
            new_lines[l] = int(layout)
            unallocated -= new_lines[l]
        elif layout.endswith('*'):
            total_props += int(layout[:-1])
    
    props_so_far = 0
    for l, layout in enumerate(layouts):
        if layout.endswith('*'):
            prop = int(layout[:-1])
            b = unallocated * (props_so_far+prop) // total_props
            a = unallocated * props_so_far // total_props
            new_lines[l] = b - a
            props_so_far += prop
    
    return new_lines

def cumsum_w_borders(arr):
    result = []
    sum = 1
    
    for elem in arr:
        result.append(sum)
        sum += elem + 1
    
    return result


class LayoutMaker:
    def __init__(self):
        classes = [
            BufferedTextWindow,
            InputWindow,
            VerticalStackLayout,
            HorizontalStackLayout
        ]

        self._class_map = {}
        for cls in classes:
            self._class_map[cls.__name__] = cls

    def make_from(self, config):
        elem_type = config['type']

        if not elem_type in self._class_map:
            raise ValueError('Unsupported layout element type', elem_type)

        root = self._class_map[elem_type]()
        windows = root.init_from_config(config)

        return root, windows