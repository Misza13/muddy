import re
import curses
import curses.ascii as asc

from pubsub import pub

import muddylib.colors as clr


class LayoutElement(object):
    def __init__(self):
        self._lines = 1
        self._columns = 1
        self._x = 1
        self._y = 1

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

    def resize(self, lines, columns, y, x):
        self._lines = lines
        self._columns = columns
        self._x = x
        self._y = y

    def init_from_config(self, config):
        raise NotImplementedError('Call of init_from_config() in base abstract class')


class Window(LayoutElement):
    def __init__(self):
        super(Window, self).__init__()
        self._name = None
        self._window = curses.newwin(1, 1, 1, 1)

    @property
    def name(self):
        return self._name

    @property
    def window(self):
        return self._window

    def init_from_config(self, config):
        self._name = config['name']
        pub.subscribe(self.message_handler, self.name)

        return [self]
    
    def resize(self, lines, columns, y, x):
        super(Window, self).resize(lines, columns, y, x)
        
        self.window.resize(lines, columns)
        self.window.mvwin(y, x)
        self.redraw()
    
    def redraw(self):
        pass

    def put_text(self, y, x, text):
        try:
            self.window.move(y ,x)
        except:
            return

        pieces = re.split('\x1b\\[(.*?)m', text)
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
                        if color == 1:  # bold/bright
                            color_num += 8
                        elif 30 <= color <= 37:  # standard 8 colors
                            color_num += color - 30
                    active_pair = curses.color_pair(color_num+1)
            else:
                try:
                    if active_pair:
                        self.window.addstr(piece, active_pair)
                    else:
                        self.window.addstr(piece)
                except:
                    # curses workaround
                    pass

            color_piece = not color_piece

    def message_handler(self, topic=pub.AUTO_TOPIC, **kwargs):
        topic = topic.getName()
        if not '.' in topic:
            return
        
        component_name, method_name = topic.split('.', 1)
        if hasattr(self, method_name):
            getattr(self, method_name)(**kwargs)


class BufferedTextWindow(Window):
    def __init__(self):
        super(BufferedTextWindow, self).__init__()
        self.window.scrollok(True)
        self.buffer = []
        self.buffer_pos = 0

    def add_text(self, text):
        if type(text) == list:
            for chunk in text:
                self.add_text(chunk)
            return
            
        self.buffer.append(text)
        if self.buffer_pos == 0:
            self.window.scroll(1)
            y, x = self.window.getmaxyx()
            self.put_text(y-1, 0, text)
            self.window.refresh()
        else:
            self.buffer_pos += 1

    def redraw(self):
        y, x = self.window.getmaxyx()

        self.window.clear()
        last_row = len(self.buffer) - self.buffer_pos - 1
        first_row = last_row - y + 1
        for l in range(last_row - first_row + 1):
            if first_row+l >= 0:
                self.window.scroll(1)
                self.put_text(y-1, 0, self.buffer[first_row+l])
        self.window.refresh()

    def scroll(self, num_rows):
        self.buffer_pos = max(self.buffer_pos - num_rows, 0)
        self.redraw()


class StaticWindow(Window):
    def __init__(self):
        super(StaticWindow, self).__init__()
        self.window.scrollok(True)
        self.buffer = []

    def redraw(self):
        self.window.clear()
        for l, line in enumerate(self.buffer):
            self.put_text(l, 0, line)
        self.window.refresh()

    def set_text(self, text):
        if type(text) == str:
            text = [text]

        self.buffer = text
        self.redraw()


DIRECTION_MAP = {
    'W': 'north',
    'S': 'south',
    'A': 'west',
    'D': 'east',
    'Q': 'down',
    'E': 'up'
}


class InputWindow(Window):
    def __init__(self):
        super(InputWindow, self).__init__()
        self.input_buffer = ''

    def refresh(self):
        self.window.refresh()

    def redraw(self):
        self.window.clear()
        self.window.addstr(self.input_buffer)
        self.window.refresh()

    def process_key(self, key):
        if key == asc.NL:
            pub.sendMessage('Core.user_input_received', input_text=self.input_buffer)
            self.input_buffer = ''
        elif key == curses.KEY_BACKSPACE or key == asc.DEL:
            if self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
        elif chr(key) in DIRECTION_MAP:
            # TODO: This belongs as a plugin (i.e.: allow interception of user keys)
            pub.sendMessage('Core.user_input_received', input_text=DIRECTION_MAP[chr(key)])
            return
        elif 0 <= key < 256:
            self.input_buffer += chr(key)
        else:
            pub.sendMessage('MainWindow.add_text', text=clr.colorify(f'Unhandled key: {key}', clr.CYAN + clr.BRIGHT))
            self.refresh()
            return
        
        self.redraw()
