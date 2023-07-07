import openpyxl
import pandas as pd
import numpy as np

from pathlib import Path


import logging

logger = logging.getLogger(__name__)


class Reader():

    # def __init__(self, given_dir, suffix=".csv"):

    #     self.dir = Path(given_dir)
    #     self.suffix = suffix
    #     self.file_paths = [file for file in self.dir.iterdir() if file.suffix == self.suffix]

    #     self.file_paths_dict = self.NameModifier()

    #     self.dfs_dict = {core_name : self.DataCleaner(file_path) for core_name, file_path in self.file_paths_dict.items()}

    def __init__(self, given_paths):

        self.file_paths = [Path(given_path) for given_path in given_paths]

        self.file_paths_dict, self.DUPLICATION = self.NameModifier()
        logger.debug(f"file_paths_dict: {self.file_paths_dict}")

        # self.dfs_dict = {core_name : self.DataCleaner(file_path) for core_name, file_path in self.file_paths_dict.items()}


    def get_dfs_dict(self):
        dfs_dict = {core_name : self.DataCleaner(file_path) for core_name, file_path in self.file_paths_dict.items()}
        return dfs_dict
            
    def NameModifier(self):
        """
        Filter the files in the given directory
        If it was in raw format, indicated by have "DLC" inside the file name, the unncessary components would be removed
        If there were both raw version and _filtered version, the _filtered version would be used
        """

        def get_core(given_file):

            status = "raw"

            if "_filtered" in given_file.stem:
                status = "filtered"

            if "DLC" in given_file.stem:
                core = given_file.stem.split("DLC")[0]
                core = " ".join(core.split(" ")[-2:])
            else:
                core = given_file.stem

            return core, status

        statuses = {}
        statuses["raw"] = {}
        statuses["filtered"] = {}

        ultilize_files = {}

        for file in self.file_paths:
            core, status = get_core(file)
            statuses[status][core] = file

        logger.debug(f"Current statuses: {statuses}")

        common_cores = set(statuses["raw"].keys()).intersection(set(statuses["filtered"].keys()))

        only_raw_cores = set(statuses["raw"].keys()).difference(set(statuses["filtered"].keys()))
        logger.debug(f"only_raw_cores: {only_raw_cores}")

        for core in only_raw_cores:
            ultilize_files[core] = statuses["raw"][core]

        for core, file in statuses["filtered"].items():
            ultilize_files[core] = file

        if common_cores:
            DUPLICATION = True
        else:
            DUPLICATION = False

        return ultilize_files, DUPLICATION
    

    def DataCleaner(self, given_path, sheet_name=None):

        if given_path.suffix == ".csv":
            df_whole = pd.read_csv(given_path, header=None)
        elif given_path.suffix == ".xlsx":
            if sheet_name is None:
                # Get all sheet names of excel_path
                wb = openpyxl.load_workbook(given_path)
                sheet_names = wb.sheetnames

                non_summary_sheets = [sheet_name for sheet_name in sheet_names if "summary" not in sheet_name.lower()]

                if len(non_summary_sheets) == 0:
                    raise Exception("No sheet name that does not contain 'summary'")
                else:
                    sheet_name = non_summary_sheets[0]

            df_whole = pd.read_excel(given_path, sheet_name=sheet_name, header=None)

        # if first row contain a cell with "scorer", remove it
        for cell in df_whole.iloc[0]:
            if "scorer" in str(cell).lower():
                df_whole = df_whole.drop(0)
                break

        # reset index
        df_whole = df_whole.reset_index(drop=True)

        # Combine the content of row 1 and row 2 into one row, f"{content of row 1} {content of row 2}", if content of row 2 is NaN, then just use content of row 1
        df_whole.iloc[0] = df_whole.iloc[0].fillna("")

        # iterate through cell in row 0
        for i, cell in enumerate(df_whole.iloc[0]):
            cell_below = df_whole.iloc[1][i]
            if cell_below is np.nan:
                df_whole.iloc[0][i] = cell
            else:
                df_whole.iloc[0][i] = f"{cell}_{cell_below}"

        # drop row 1
        df_whole = df_whole.drop(1)

        # make row 0 as header
        df_whole.columns = df_whole.iloc[0]

        # drop row 0
        df_whole = df_whole.drop(0)

        # reset index
        df_whole = df_whole.reset_index(drop=True)

        for column in df_whole.columns:
            if "likelihood" in column.lower():
                df_whole = df_whole.drop(column, axis=1)

        logger.debug(f"Cleaned data frame with columns: {df_whole.columns}")
    #     ['bodyparts_coords', 'heart1_x', 'heart1_y', 'heart2_x', 'heart2_y',
    #    'heart3_x', 'heart3_y', 'heart4_x', 'heart4_y', 'heart5_x', 'heart5_y',
    #    'heart6_x', 'heart6_y', 'heart7_x', 'heart7_y', 'heart8_x', 'heart8_y']

        return df_whole


        

        