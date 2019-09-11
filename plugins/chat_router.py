import re

from muddylib.plugins import MuddyPlugin, IncomingTextHandler


class ChatRouterPlugin(MuddyPlugin):
    chat_rx = re.compile(r'^({chan ch=(?P<chan>.*?)\}|{say}|{tell})(?P<text>.*)$')
    
    @IncomingTextHandler
    def handle(self, line):
        chat_m = self.chat_rx.search(line)
        if chat_m:
            self.invoke_method('ChatWindow', 'add_text', text=chat_m['text'])
            return True

        return False
