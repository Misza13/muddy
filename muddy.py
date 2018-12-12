import threading
import re
import json

from pubsub import pub

import curses
import curses.ascii as asc

from twisted.internet import reactor

from muddylib.screen import MudScreen
from muddylib.telnet import MudClientFactory, ConnectionKeeper


class MudWindowSession:
    def __init__(self, screen):
        curses.noecho()
        curses.cbreak()

        curses.start_color()
        for c in range(16):
            curses.init_pair(c+1, c, curses.COLOR_BLACK)

        self.screen = screen
        screen_config = json.loads(open('config/aardwolf_windows.json', 'r').read())
        self.mud_screen = MudScreen(screen, screen_config)
        
        self.connection_keeper = ConnectionKeeper()
        pub.subscribe(self._route_incoming_text, 'Core.telnet_received')
        pub.subscribe(self._input_handler, 'Core.user_input_received')
        
        self.app_running = True

    def main_loop(self):
        f = MudClientFactory(lambda x: self._handle_connection_created(x))
        reactor.connectTCP('aardmud.org', 4000, f)
        def rrun():
            reactor.run(installSignalHandlers=0)
        r_thread = threading.Thread(target=rrun)
        r_thread.start()
        
        self.mud_screen.refresh_all()
        while self.app_running:
            key = self.screen.getch()
            self._key_handler(key)

        r_thread.join()

    def write_to_main_window(self, text):
        pub.sendMessage('MainWindow.add_text', text=text)
        pub.sendMessage('InputWindow.refresh')
    
    def _route_incoming_text(self, text):
        if type(text) == str:
            text = [text]
        
        for line in text:
            chat_rx = re.compile(r'^(\{chan ch=(?P<chan>.*?)\}|\{say\})(?P<text>.*)$')
            chat_m = chat_rx.search(line)
            if chat_m:
                pub.sendMessage('ChatWindow.add_text', text=chat_m['text'])
            else:
                pub.sendMessage('MainWindow.add_text', text=line)
        
        pub.sendMessage('InputWindow.refresh')

    def _key_handler(self, key):
        if key == curses.KEY_RESIZE:
            self.mud_screen.refresh_all()
            pub.sendMessage('InputWindow.refresh')
        elif key == asc.ESC:
            key = self.screen.getch()
            self._escape_key_handler(key)
        elif key == -1:
            pass
        elif key == curses.KEY_PPAGE:
            pub.sendMessage('MainWindow.scroll', num_rows=-10)
            pub.sendMessage('InputWindow.refresh')
        elif key == curses.KEY_NPAGE:
            pub.sendMessage('MainWindow.scroll', num_rows=10)
            pub.sendMessage('InputWindow.refresh')
        else:
            pub.sendMessage('InputWindow.process_key', key=key)

    def _escape_key_handler(self, key):
        if key == ord('q'):
            self.app_running = False
            self.connection_keeper.disconnect()
            reactor.stop()
            return

        self.write_to_main_window('\x1b[36;1mUnhandled escape key: ' + str(key) + '\x1b[0m')

    def _input_handler(self, input_text):
        self.write_to_main_window('\x1b[33m' + input_text + '\x1b[0m')
        self.connection_keeper.send_data(input_text)
    
    def _handle_connection_created(self, proto):
        self.connection_keeper.register(proto)


def main(screen):
    sess = MudWindowSession(screen)

    sess.main_loop()


if __name__ == '__main__':
    curses.wrapper(main)
