import tkinter
from tkinter import ttk

class ProgressWindow(tkinter.Toplevel):
        
    def __init__(self, master, title="Analysis Progress", geometry="300x100"):
        tkinter.Toplevel.__init__(self, master)
        self.title(title)
        self.geometry(geometry)

        FONT = ('Helvetica', 14, 'bold')

        self.total_label = tkinter.Label(self, text="Total Progress", font=FONT)
        self.total_label.pack(pady=5)
        self.total = ttk.Progressbar(self, length=100, mode='determinate')
        self.total.pack(pady=5)

    def update_progress(self, value, text="Calculating End Points"):
        self.total_label["text"] = text
        self.total["value"] = value
        self.update()