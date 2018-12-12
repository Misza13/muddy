import re

from pubsub import pub

from muddylib.plugins import IncomingTextHandler

class ChatRouterPlugin:
    @IncomingTextHandler
    def handle(self, line):
        chat_rx = re.compile(r'^(\{chan ch=(?P<chan>.*?)\}|\{say\})(?P<text>.*)$')
        chat_m = chat_rx.search(line)
        if chat_m:
            pub.sendMessage('ChatWindow.add_text', text=chat_m['text'])
            return True

        return False