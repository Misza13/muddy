import re

from muddylib.plugins import MuddyPlugin, IncomingTextHandler


class MinimapRouterPlugin(MuddyPlugin):
    def __init__(self):
        self.buffer = []
        self.collecting_map = False

    @IncomingTextHandler
    def handle(self, line):
        if re.search(r'^<MAPSTART>$', line):
            self.buffer = []
            self.collecting_map = True
            return True
        elif re.search(r'^(\x1b\[0;37m)?<MAPEND>$', line):
            self.collecting_map = False
            self.invoke_method('MinimapWindow', 'set_text', text=self.buffer)
            return True
        elif self.collecting_map:
            self.buffer.append(line)
            return True
        else:
            return False