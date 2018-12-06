import sys
import threading
import re

import curses
import curses.ascii as asc

from twisted.internet import reactor

from muddylib.telnet import MudProtocol, MudClientFactory, ConnectionKeeper
from muddylib.windows import BufferedTextWindow, InputWindow


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
        
        self.connection_keeper = ConnectionKeeper()
        
        self.app_running = True

    def main_loop(self):
        f = MudClientFactory(
            lambda x: self._route_incoming_text(x),
            lambda x: self._handle_connection_created(x))
        reactor.connectTCP('aardmud.org', 4000, f)
        def rrun():
            reactor.run(installSignalHandlers=0)
        r_thread = threading.Thread(target=rrun)
        r_thread.start()
        
        self.refresh_all()
        while self.app_running:
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
        elif key == asc.ESC:
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
        if key == ord('q'):
            self.app_running = False
            self.connection_keeper.disconnect()
            reactor.stop()
            return

        self.write_to_main_window('Unhandled escape key: ' + str(key))

    def _input_handler(self, input_text):
        self.write_to_main_window(input_text)
        self.connection_keeper.send_data(input_text)
    
    def _handle_connection_created(self, proto):
        self.connection_keeper.register(proto)


def main(screen):
    sess = MudWindowSession(screen)

    sess.main_loop()


if __name__ == '__main__':
    curses.wrapper(main)
