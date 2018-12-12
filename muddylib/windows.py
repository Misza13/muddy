import re
import curses
import curses.ascii as asc

from pubsub import pub


class Window:
    def __init__(self, name, lines, columns, y, x):
        self._name = name
        self._lines = lines
        self._columns = columns
        self._y = y
        self._x = x
        self._window = curses.newwin(lines, columns, y, x)
        
        pub.subscribe(self.message_handler, name)

    @property
    def name(self):
        return self._name

    @property
    def lines(self):
        return self._lines

    @property
    def columns(self):
        return self._columns

    @property
    def y(self):
        return self._y

    @property
    def x(self):
        return self._x

    @property
    def window(self):
        return self._window
    
    def message_handler(self, topic=pub.AUTO_TOPIC, **kwargs):
        topic = topic.getName()
        if not '.' in topic:
            return
        
        component_name, method_name = topic.split('.', 1)
        if hasattr(self, method_name):
            getattr(self, method_name)(**kwargs)


class BufferedTextWindow(Window):
    def __init__(self, name, lines, columns, y, x):
        super().__init__(name, lines, columns, y, x)
        self.window.scrollok(True)
        self.buffer = []
        self.buffer_pos = 0

    def add_text(self, text):
        self.buffer.append(text)
        if self.buffer_pos == 0:
            self.draw_text(text)
        else:
            self.buffer_pos += 1

    def draw_text(self, text):
        self.window.scroll(1)
        y, x = self.window.getmaxyx()
        self.put_text(y-1, 0, text)
        self.window.refresh()

    def put_text(self, y, x, text):
        self.window.move(y ,x)

        pieces = re.split('\x1b\[(.*?)m', text)
        color_piece = False
        active_pair = None
        for piece in pieces:
            if color_piece:
                if piece == '0':
                    active_pair = None
                else:
                    color_num = 0
                    colors = [int(c) for c in piece.split(';')]
                    for color in colors:
                        if color == 1: #bold/bright
                            color_num += 8
                        elif color >= 30 and color <= 37: # standard 8 colors
                            color_num += color - 30
                    active_pair = curses.color_pair(color_num+1)
            else:
                if active_pair:
                    self.window.addstr(piece, active_pair)
                else:
                    self.window.addstr(piece)

            color_piece = not color_piece

    def redraw(self):
        y, x = self.window.getmaxyx()

        self.window.clear()
        last_row = len(self.buffer) - self.buffer_pos - 1
        first_row = last_row - y + 1
        for l in range(last_row - first_row + 1):
            if first_row+l >= 0:
                self.put_text(l, 0, self.buffer[first_row+l])
        self.window.refresh()

    def resize(self, lines, columns, y, x):
        self.window.resize(lines, columns)
        self.window.mvwin(y, x)
        self.redraw()

    def scroll(self, num_rows):
        self.buffer_pos = max(self.buffer_pos - num_rows, 0)
        self.redraw()


class InputWindow(Window):
    def __init__(self, name, columns, y, x):
        super().__init__(name, 1, columns, y, x)
        self.input_buffer = ''

    def refresh(self):
        self.window.refresh()

    def redraw(self):
        self.window.clear()
        self.window.addstr(self.input_buffer)
        self.window.refresh()

    def resize(self, columns, y, x):
        self.window.resize(1, columns)
        self.window.mvwin(y, x)
        self.redraw()

    def process_key(self, key):
        if key == asc.NL:
            pub.sendMessage('Core.user_input_received', input_text=self.input_buffer)
            self.input_buffer = ''
        elif key == curses.KEY_BACKSPACE or key == asc.DEL:
            if self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
        elif key >= 0 and key < 256:
            self.input_buffer += chr(key)
        else:
            pub.sendMessage('MainWindow.add_text', text='\x1b[36;1mUnhandled key: ' + str(key) + '\x1b[0m')
            self.refresh()
            return
        
        self.redraw()