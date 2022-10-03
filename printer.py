import os, cursor
from colorama import init, Cursor

class Printer:
    def __init__(this):
        this.text=""
        this.previous_rows = 0
        init()
        os.system('cls')
        cursor.hide()
    
    def clear_q(this):
        this.text=""
        
    def print(this, s="", end="\n"):
        this.text += str(s) + "\x1b[0K" + str(end)
        
    def draw(this):
        print(this.text, end="\x1b[0K", flush=True)
        
    def reset_cursor(this):
        print(Cursor.POS(1, 1), end="")