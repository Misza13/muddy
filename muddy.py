import time
import sys
import threading
import zlib
import re

import curses
import curses.ascii as asc

from twisted.internet.protocol import ClientFactory
from twisted.conch.telnet import Telnet
from twisted.internet import reactor


from muddylib.windows import BufferedTextWindow, InputWindow


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
        lines = [line.strip('\r') for line in data.split('\n')]
        self.recv_handler(lines)

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
        
        x_split = x * 2 // 3

        self.main_window = BufferedTextWindow(y-4, x_split-2, 1, 1)
        self.chat_window = BufferedTextWindow(y-4, x-x_split-2, 1, x_split+1)

        self.input = InputWindow(x-2, y-2, 1, lambda t: self._input_handler(t))

    def main_loop(self):
        f = MudClientFactory(lambda x: self._route_incoming_text(x))
        reactor.connectTCP('aardmud.org', 4000, f)
        def rrun():
            reactor.run(installSignalHandlers=0)
        r_thread = threading.Thread(target=rrun)
        r_thread.start()
        
        self.refresh_all()
        while app_running:
            key = self.screen.getch()
            self._key_handler(key)

        r_thread.join()

    def refresh_all(self):
        y, x = self.screen.getmaxyx()
        self.screen.clear()
        
        x_split = x * 2 // 3

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
            self.screen.addch(y_b, x_split-1, '#')
            self.screen.addch(y_b, x-1, '#')

        self.screen.refresh()
        self.main_window.resize(y-4, x_split-2, 1, 1)
        self.chat_window.resize(y-4, x-x_split-2, 1, x_split+1)
        self.input.resize(x-2, y-2, 1)

    def write_to_main_window(self, text):
        self._route_incoming_text(text)
        self.input.redraw()
    
    def _route_incoming_text(self, text):
        if type(text) == str:
            text = [text]
        
        for line in text:
            chat_rx = re.compile(r'^(\{chan ch=(?P<chan>.*?)\}|\{say\})(?P<text>.*)$')
            chat_m = chat_rx.search(line)
            if chat_m:
                self.chat_window.add_text(chat_m['text'])
            else:
                self.main_window.add_text(line)
        
        self.input.redraw()

    def _key_handler(self, key):
        #if key == asc.NL and self.last_key == asc.NL:
        #    self.last_key = None
        #    return

        self.last_key = key

        if key == curses.KEY_RESIZE:
            self.refresh_all()
        elif key == 27:
            key = self.screen.getch()
            self._escape_key_handler(key)
        elif key == -1:
            pass
        elif key == curses.KEY_PPAGE:
            self.main_window.scroll(-10)
            self.input.redraw()
        elif key == curses.KEY_NPAGE:
            self.main_window.scroll(10)
            self.input.redraw()
        else:
            if not self.input.process_key(key):
                self.write_to_main_window('Unhandled key: ' + str(key))

    def _escape_key_handler(self, key):
        if key == 113: #q
            global app_running
            app_running = False
            global clients
            clients[0].transport.loseConnection()
            reactor.stop()
            return

        self.write_to_main_window('Unhandled escape key: ' + str(key))

    def _input_handler(self, input_text):
        self.write_to_main_window(input_text)
        clients[0].sendData(input_text)


def main(screen):
    sess = MudWindowSession(screen)

    sess.main_loop()


if __name__ == '__main__':
    curses.wrapper(main)
