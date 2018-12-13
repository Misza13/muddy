import re

from pubsub import pub

from muddylib.plugins import IncomingTextHandler


class MinimapRouterPlugin:
    def __init__(self):
        self.buffer = []
        self.collecting_map = False

    @IncomingTextHandler
    def handle(self, line):
        if re.search(r'^<MAPSTART>$', line):
            self.buffer = []
            self.collecting_map = True
            return True
        elif re.search(r'^<MAPEND>$', line):
            self.collecting_map = False
            pub.sendMessage('MinimapWindow.set_text', text=self.buffer)
            return True
        elif self.collecting_map:
            self.buffer.append(line)
            return True
        else:
            return False