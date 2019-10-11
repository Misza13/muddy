import curses

from muddylib.session import session_main

if __name__ == '__main__':
    curses.wrapper(session_main)
