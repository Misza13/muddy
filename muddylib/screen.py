from muddylib.windows import BufferedTextWindow, InputWindow


class MudScreen(object):
    def __init__(self, screen):
        self.screen = screen
        self.screen.keypad(True)
        self.screen.scrollok(False)
        
        y, x = screen.getmaxyx()
        x_split = x * 2 // 3

        self.main_window = BufferedTextWindow('MainWindow')
        self.chat_window = BufferedTextWindow('ChatWindow')

        self.input = InputWindow('InputWindow')

    def refresh_all(self):
        self.screen.clear()

        y, x = self.screen.getmaxyx()
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