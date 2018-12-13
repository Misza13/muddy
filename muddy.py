import traceback
import threading
import json

from pubsub import pub

import curses
import curses.ascii as asc

from twisted.internet import reactor

import muddylib.colors as clr
from muddylib.screen import MudScreen
from muddylib.telnet import MudClientFactory, ConnectionKeeper
from muddylib.plugins import PluginManager

from plugins.chat_router import ChatRouterPlugin
from plugins.minimap_router import MinimapRouterPlugin
from plugins.aardwolf_stats import AardwolfStatsPlugin


class MudWindowSession:
    def __init__(self, screen):
        self.logger = open('muddy.log', 'w+')
        
        self.plugin_manager = PluginManager()

        self.plugin_manager.register_plugin(ChatRouterPlugin())
        self.plugin_manager.register_plugin(MinimapRouterPlugin())
        self.plugin_manager.register_plugin(AardwolfStatsPlugin())

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
            self.logger.write(repr(line) + '\n')
        self.logger.flush()
        
        for line in text:
            routed = False
            for handler in self.plugin_manager.get_handlers('IncomingTextHandler'):
                try:
                    if handler(line):
                        routed = True
                        break
                except:
                    pub.sendMessage(
                        'MainWindow.add_text',
                        text=clr.colorify('Error occured when processing handler:', clr.RED + clr.BRIGHT))
                    pub.sendMessage(
                        'MainWindow.add_text',
                        text=[clr.colorify(l, clr.RED + clr.BRIGHT) for l in traceback.format_exc().split('\n')])

            if not routed:
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
