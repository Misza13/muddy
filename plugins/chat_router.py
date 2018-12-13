import re

from pubsub import pub

from muddylib.plugins import IncomingTextHandler

class ChatRouterPlugin:
    chat_rx = re.compile(r'^(\{chan ch=(?P<chan>.*?)\}|\{say\}|\{tell\})(?P<text>.*)$')
    
    @IncomingTextHandler
    def handle(self, line):
        chat_m = self.chat_rx.search(line)
        if chat_m:
            pub.sendMessage('ChatWindow.add_text', text=chat_m['text'])
            return True

        return False