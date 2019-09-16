#/bin/python

from subprocess import check_call
from tkinter import *

def callH(dialstring, calltime):
    master.destroy()

def errorWindow(message):
    Label(master, text=message).grid(sticky=W, columnspan=2)

def return_deep_link(event=None):
    global deep_link
    deep_link = e.get()
    master.destroy()


def input_window(window_name, action, org):
    global master
    master = Tk()
    Label(master, text=window_name).grid(sticky=W)
    global e
    e = Entry(master)
    e.grid(row=0,column=1)
    e.focus_set()

    def enter_deep_link(event):
        deep_link=e.get()
        action(org, deep_link)
        master.destroy()
    master.bind('<Return>', enter_deep_link)
    mainloop()
