import sys
import threading
import zlib
import re

import curses
import curses.ascii as asc

from twisted.internet.protocol import ClientFactory
from twisted.conch.telnet import Telnet
from twisted.internet import reactor


app_running = True


class MudProtocol(Telnet):
    def __init__(self, recv_handler):
        super().__init__()
        self.recv_handler = recv_handler
        self.decompress = zlib.decompressobj()
        self.negotiationMap[b'V'] = lambda data: self.compression_negotiated(data)
        self.compression_enabled = False

    def telnet_WILL(self, option):
        if option == b'V':
            self.do(b'V')

    def compression_negotiated(self, data):
        self.compression_enabled = True

    def dataReceived(self, data):
        if self.compression_enabled:
            data = self.decompress.decompress(data)

        Telnet.dataReceived(self, data)

    def applicationDataReceived(self, data):
        data = data.decode()
        for line in data.split('\n'):
            self.recv_handler(line)

    def sendData(self, data):
        data += '\n'
        self.transport.write(data.encode('ascii'))

    def connectionLost(self, reason):
        self.recv_handler('Connection lost: ' + str(reason))


clients = []


class MudClientFactory(ClientFactory):
    def __init__(self, recv_handler):
        self.recv_handler = recv_handler

    def buildProtocol(self, addr):
        global clients

        proto = MudProtocol(self.recv_handler)
        clients.append(proto)

        return proto


class BufferedTextWindow:
    def __init__(self, lines, columns, y, x):
        self.window = curses.newwin(lines, columns, y, x)
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


class InputWindow:
    def __init__(self, columns, y, x, input_handler):
        self.window = curses.newwin(1, columns, y, x)
        self.input_buffer = ''
        self.input_handler = input_handler

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
            self.input_handler(self.input_buffer)
            self.input_buffer = ''
        else:
            self.input_buffer += chr(key)
        self.redraw()


class MudWindowSession:
    def __init__(self, screen):
        self.last_key = None

        curses.noecho()
        curses.cbreak()

        curses.start_color()
        for c in range(16):
            curses.init_pair(c+1, c, curses.COLOR_BLACK)

        y, x = screen.getmaxyx()

        self.screen = screen
        self.screen.keypad(True)
        self.screen.scrollok(False)

        self.main_window = BufferedTextWindow(y-4, x-2, 1, 1)

        self.input = InputWindow(x-2, y-2, 1, lambda t: self._input_handler(t))

    def main_loop(self):
        f = MudClientFactory(lambda x: self.write_to_main_window(x))
        reactor.connectTCP('aardmud.org', 4000, f)
        r_thread = threading.Thread(target=reactor.run)
        r_thread.start()

        self.refresh_all()
        while app_running:
            key = self.screen.getch()
            self._key_handler(key)

        r_thread.join()

    def refresh_all(self):
        y, x = self.screen.getmaxyx()
        self.screen.clear()

        # Horizontal lines
        for x_b in range(x):
            self.screen.addch(0, x_b, '#')
            self.screen.addch(y-3, x_b, '#')
            try:
                self.screen.addch(y-1, x_b, '#')
            except:
                pass

        # Vertical lines
        for y_b in range(1, y-1):
            self.screen.addch(y_b, 0, '#')
            self.screen.addch(y_b, x-1, '#')

        self.screen.refresh()
        self.main_window.resize(y-4, x-2, 1, 1)
        self.input.resize(x-2, y-2, 1)

    def write_to_main_window(self, text):
        self.main_window.add_text(text)
        self.input.redraw()

    def _key_handler(self, key):
        if key == asc.NL and self.last_key == asc.NL:
            self.last_key = None
            return

        self.last_key = key

        if key == curses.KEY_RESIZE:
            self.refresh_all()
        elif key == 27:
            key = self.screen.getch()
            self._escape_key_handler(key)
        elif key <= 255:
            self.input.process_key(key)
        elif key == curses.KEY_PPAGE:
            self.main_window.scroll(-10)
            self.input.redraw()
        elif key == curses.KEY_NPAGE:
            self.main_window.scroll(10)
            self.input.redraw()
        else:
            self.write_to_main_window('Unsupported key: ' + str(key))

    def _escape_key_handler(self, key):
        if key == 113: #q
            global app_running
            app_running = False
            global clients
            clients[0].transport.loseConnection()
            reactor.stop()
            return

        self.write_to_main_window('Alt key: ' + str(key))

    def _input_handler(self, input_text):
        self.write_to_main_window(input_text)
        clients[0].sendData(input_text)


def main(screen):
    sess = MudWindowSession(screen)

    sess.main_loop()


if __name__ == '__main__':
    curses.wrapper(main)
