import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import os
from pathlib import Path
from colorlog import ColoredFormatter

from Libs.analyzer import Analyzer
from Libs.reader import Reader
from Libs.utils import draw_peaks
from Libs.customwidgets import ProgressWindow
from Libs import ENTRY_NAMES, ENTRY_NAMES_SET1, ENTRY_NAMES_SET2, DEFAULT_VALUES

###################################################### SETUP LOGGING ######################################################

import logging
logger = logging.getLogger(__name__)

# save log to Log/log.txt
Path('Log').mkdir(parents=True, exist_ok=True)

# Configure the logging module
log_file = 'Log/app.log'

class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.
    """

    def filter(self, record):
        record.pathname = os.path.basename(record.pathname)  # Modify this line if you want to alter the path
        return True

# Define the log format with colors
log_format = "%(asctime)s %(log_color)s%(levelname)-8s%(reset)s [%(pathname)s] %(message)s"

# Create a formatter with colored output
formatter = ColoredFormatter(log_format)

# Get the root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create a filter
f = ContextFilter()

# Create a file handler to save logs to the file
file_handler = logging.FileHandler(log_file, mode='a')  # Set the mode to 'a' for append
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s [%(pathname)s] %(message)s"))
file_handler.addFilter(f)  # Add the filter to the file handler
file_handler.setLevel(logging.DEBUG)

# Create a stream handler to display logs on the console with colored output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.addFilter(f)  # Add the filter to the stream handler
stream_handler.setLevel(logging.DEBUG)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

#################################################### MAIN APPLICATION ####################################################

import tkinter as tk
from tkinter import filedialog
from pathlib import Path

class Application(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Cardiac Performance Analyzer - dlc")

        self.TOLERANCE = None
        
        self.left_frame = tk.Frame(self)
        self.mid_frame = tk.Frame(self)
        self.right_frame = tk.Frame(self)

        self.left_frame.pack(side=tk.LEFT)
        self.mid_frame.pack(side=tk.LEFT)
        self.right_frame.pack(side=tk.RIGHT)

        BUTTON_CONFIG = {'padx': 10,
                         'pady': 10,
                         'fg': 'white',
                         'bg': '#496278',
                         'font': ('Arial', 14, 'bold'),}

        self.file_button = tk.Button(self.left_frame, text='Open File(s)', command=self.open_files)
        self.find_tolerance_button = tk.Button(self.left_frame, text='Find Tolerance', command=self.find_tolerance)
        self.analyze_button = tk.Button(self.left_frame, text='Analyze', command=self.analyze)
        self.display_button = tk.Button(self.left_frame, text='Display Peaks', command=self.displaypeaks)

        self.file_button.config(BUTTON_CONFIG)
        self.find_tolerance_button.config(BUTTON_CONFIG)
        self.analyze_button.config(BUTTON_CONFIG)
        self.display_button.config(BUTTON_CONFIG)

        self.file_button.pack()
        self.find_tolerance_button.pack()
        self.analyze_button.pack()
        self.display_button.pack()

        # disable find_tolerance_button, analyze_button, display_button on start
        self.find_tolerance_button.config(state=tk.DISABLED)
        self.analyze_button.config(state=tk.DISABLED)
        self.display_button.config(state=tk.DISABLED)

        self.right_frame.pack_forget() # Hide RightFrame on start

        self.selected_files = []

        self.entries = {name : None for name in ENTRY_NAMES}
        self.files_widgets = {}


    def reset_entries(self):
        self.entries = {name : None for name in ENTRY_NAMES}
        if self.files_widgets != {}:
            for obj in self.files_widgets.values():
                if isinstance(obj, dict):
                    for widget in obj.values():
                        widget.destroy()
                else:
                    obj.destroy()
        self.files_widgets = {}


    def post_open_check(self):
        if len(self.selected_files) == 0:
            logger.warning('No files selected')
            return False
        
        temp_reader = Reader(self.selected_files)
        if temp_reader.DUPLICATION == False:
            logger.info("No duplication found")
            return True
        else:
            message = 'Both unfiltered and filtered version of the same file(s) were found'
            message += '\nPress Yes if you want to load only the Filtered version'
            message += '\nPress No if you want to load both versions'
            choice = tk.messagebox.askyesno('Duplicates found', message)
            if choice:
                self.selected_files = list(temp_reader.file_paths_dict.values())
                logger.info("Load only filtered version of the file(s)")
            return True                

    def open_files(self):
        self.selected_files = filedialog.askopenfilenames()
        for widget in self.mid_frame.winfo_children():
            widget.destroy() 

        NO_ERROR = self.post_open_check()

        if not NO_ERROR:
            return          

        self.reset_entries()
        self.find_tolerance_button.config(state=tk.NORMAL)


        if len(self.selected_files) == 1:

            for entry in ENTRY_NAMES_SET1:
                row = tk.Frame(self.mid_frame)
                label = tk.Label(row, text=entry, width=20)
                self.entries[entry] = tk.Entry(row)
                row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                label.pack(side=tk.LEFT)
                self.entries[entry].pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
                if entry in list(DEFAULT_VALUES.keys()):
                    self.entries[entry].insert(0, DEFAULT_VALUES[entry])
        else:

            mid_frame_top = tk.Frame(self.mid_frame)
            mid_frame_bottom = tk.Frame(self.mid_frame)
            mid_frame_top.pack(side=tk.TOP, fill=tk.X)
            mid_frame_bottom.pack(side=tk.BOTTOM, fill=tk.X)

            copy_params_button = tk.Button(mid_frame_top, 
                                           text='Copy parameters from first row to other rows',
                                           command=self.copy_params_from_first_row)
            copy_params_button.pack()

            for file in self.selected_files:
                file_name = Path(file).name
                self.files_widgets[file_name] = {}
                self.files_widgets[file_name]['row'] = tk.Frame(mid_frame_bottom)
                self.files_widgets[file_name]['label'] = tk.Label(self.files_widgets[file_name]['row'], text=file_name, width=20)
                self.files_widgets[file_name]['row'].pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                self.files_widgets[file_name]['label'].pack(side=tk.LEFT)

                for entry in ENTRY_NAMES_SET1:
                    self.files_widgets[file_name][entry] = tk.Entry(self.files_widgets[file_name]['row'])
                    self.files_widgets[file_name][entry].pack(side=tk.LEFT, expand=tk.YES, fill=tk.X, padx=5, pady=5)
                    if entry in list(DEFAULT_VALUES.keys()):
                        self.files_widgets[file_name][entry].insert(0, DEFAULT_VALUES[entry])


    def entries_checker(self, entry_dict):

        NULL_LIST = []

        for param_name, entry in entry_dict.items():
            if entry == None:
                continue
            try:
                entry_value = float(entry.get())
            except:
                continue

            if entry_value == '' and param_name in list(DEFAULT_VALUES.keys()):
                NULL_LIST.append(param_name)
        
        if NULL_LIST:
            tk.messagebox.showerror(title='Error', message=f'Please fill in the following parameters: {NULL_LIST}')
            return False
        
        return True
    

    def find_tolerance(self):

        if len(self.selected_files) == 1:
            if not self.entries_checker(self.entries):
                return
            
            PARAMS = {}
            for param in ENTRY_NAMES_SET1:
                PARAMS[param] = self.get_current_entry_value(param)

            analyzer = Analyzer(self.selected_files[0], PARAMS)
            analyzer.df_Loader(get_tolerance=True)

            self.TOLERANCE = analyzer.tolerance

            for entry in ENTRY_NAMES_SET2:
                row = tk.Frame(self.mid_frame)
                label = tk.Label(row, text=entry, width=20)
                self.entries[entry] = tk.Entry(row)
                row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
                label.pack(side=tk.LEFT)
                self.entries[entry].pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
                

            self.entries['TOLERANCE'].insert(0, self.TOLERANCE)

        else:
            for file in self.selected_files:
                logger.debug(f"Finding tolerance for {file}")
                file_name = Path(file).name

                if not self.entries_checker(self.files_widgets[file_name]):
                    return

                PARAMS = {}
                for param in ENTRY_NAMES_SET1:
                    PARAMS[param] = self.get_current_entry_value(param, file_name=file_name)

                analyzer = Analyzer(file, PARAMS)
                analyzer.df_Loader(get_tolerance=True)

                self.TOLERANCE = analyzer.tolerance

                self.files_widgets[file_name]["TOLERANCE"] = tk.Entry(self.files_widgets[file_name]['row'])
                self.files_widgets[file_name]["TOLERANCE"].pack(side=tk.LEFT, expand=tk.YES, fill=tk.X, padx=5, pady=5)
                self.files_widgets[file_name]['TOLERANCE'].insert(0, self.TOLERANCE)


        self.analyze_button.config(state=tk.NORMAL)


    def copy_params_from_first_row(self):
        if self.files_widgets == {}:
            return
        
        first_file_name = list(self.files_widgets.keys())[0]
        if self.entries_checker(self.files_widgets[first_file_name]) == False:
            tk.messagebox.showerror(title='Error', message=f'Please fill in the parameters of the first row')
            return
        
        for file_name, file_params in self.files_widgets.items():
            if file_name == first_file_name:
                continue
            for param_name, param_entry in file_params.items():
                if param_name == 'row' or param_name == 'label':
                    continue
                param_entry.delete(0, tk.END)
                param_entry.insert(0, self.files_widgets[first_file_name][param_name].get())


    def get_entry_from_entryname(self, entry_name, file_name=None):
        if file_name == None:
            try:
                given_entry = self.entries[entry_name]
            except:
                given_entry = None
        else:
            try:
                given_entry = self.files_widgets[file_name][entry_name]
            except:
                given_entry = None

        return given_entry

    
    def get_current_entry_value(self, entry_name, file_name=None):
        given_entry = self.get_entry_from_entryname(entry_name, file_name=file_name)

        if given_entry == None:
            logger.debug(f"Entry {entry_name} not found, returning value = None")
            return None

        try:
            current_value = given_entry.get()
            if current_value == '':
                current_value = None
        except:
            current_value = None

        try:
            current_value = float(current_value)
            logger.debug(f"Converted value of {entry_name} to float: {current_value}")
        except:
            pass

        return current_value


    def get_all_params(self):
        if len(self.selected_files) == 1:
            if not self.entries_checker(self.entries):
                return
            
            PARAMS = {}
            for param in ENTRY_NAMES:
                PARAMS[param] = self.get_current_entry_value(param)
            
            return PARAMS

        else:
            PARAMS = {}
            for file in self.selected_files:
                file_name = Path(file).name

                if not self.entries_checker(self.files_widgets[file_name]):
                    return

                PARAMS[file_name] = {}
                for param in ENTRY_NAMES:
                    PARAMS[file_name][param] = self.get_current_entry_value(param, file_name=file_name)
            
            return PARAMS

    def create_progress_bar(self):
        self.progress_bar = ttk.Progressbar(self.bottom_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=5, pady=5)



    
    def analyze(self):  
        PARAMS = self.get_all_params()

        PROGRESS_WINDOW = ProgressWindow(self)

        if len(self.selected_files) == 1:
            analyzer = Analyzer(self.selected_files[0], PARAMS)
            self.core_name = analyzer.core_name
            analyzer.df_Loader()
            self.values_for_draw = analyzer.Peak_Finder()
            analyzer.EndPoints_Calculator()
            analyzer.EndPoints_Updater()

            tk.messagebox.showinfo(title='Success', message=f'Analysis of {Path(self.selected_files[0]).name} is done!')

            # Change text of self.display_button to 'Display & Save Peaks'
            self.display_button.config(text='Display Peaks')
            self.display_button.config(state=tk.NORMAL)

        else:
            for i, file in enumerate(self.selected_files):
                file_name = Path(file).name
                analyzer = Analyzer(file, PARAMS[file_name])
                analyzer.df_Loader()
                analyzer.Peak_Finder()
                analyzer.EndPoints_Calculator()
                analyzer.EndPoints_Updater()
                analyzer.SavePeaks()

                progress = int((i+1)/len(self.selected_files)*100)
                PROGRESS_WINDOW.update_progress(progress)

            tk.messagebox.showinfo(title='Success', message=f'Batch analysis of {len(self.selected_files)} files is done!')

            # Change text of self.display_button to 'Save Peaks'
            self.display_button.config(text='Save Peaks')



    def displaypeaks(self):
        
        draw_peaks(master=self, 
                   given_name=self.core_name, 
                   given_values=self.values_for_draw, 
                   mode="display")
        
        logger.debug(f"Displaying peaks of {self.core_name} is done!")

        draw_peaks(master=self, 
                   given_name=self.core_name, 
                   given_values=self.values_for_draw, 
                   mode="save")



if __name__ == "__main__":
    app = Application()
    app.mainloop()
