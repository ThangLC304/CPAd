import numpy as np

from Libs.reader import *
from Libs.calculations import PeakFinder, SDCalculator
from Libs.utils import make_df
from . import ALLOWED_DECIMALS, SUMMARY_PATH, SUMMARY_FILE_COLUMNS

class Analyzer:

    def __init__(self, given_path, PARAMS):

        self.given_path = given_path
        self.PARAMS = PARAMS

        reader = Reader(given_paths = [given_path])

        dfs_dict = reader.dfs_dict
        for core_name, df in dfs_dict.items():
            dfs_dict[core_name] = self.cleaner(df)
            
        self.cleaned_df = list(dfs_dict.values())[0]

        try:
            self.tolerance = PARAMS["TOLERANCE"]
            logger.info(f"Tolerance found in PARAMS, using value {self.tolerance}")
        except KeyError:
            self.tolerance = 0.1
            logger.warning("Tolerance not found in PARAMS, using default value 0.1")

        logger.debug(f"PARAMS: {PARAMS}")
    
    def cleaner(self, given_df):

        excepted_columns = []
        for column in given_df.columns:
            if any([f"heart{num}" in column.lower() for num in [1, 3, 5, 7]]):
                excepted_columns.append(column)

        cleaned_df = given_df[excepted_columns]

        # change all values in cleaned_df to float
        cleaned_df = cleaned_df.astype(float)

        return cleaned_df
    

    def df_Loader(self, get_tolerance=False):

        cleaned_df = self.cleaned_df

        FRAMES = len(cleaned_df)

        LAD_in_pixel = []
        LAD_in_mm = []

        SAD_in_pixel = []
        SAD_in_mm = []

        Heart_Volumes_in_mm3 = []
        Heart_Volumes_in_pL = []

        for i in range(FRAMES):
            h5x = cleaned_df.iloc[i]["heart5_x"]
            h5y = cleaned_df.iloc[i]["heart5_y"]
            h1x = cleaned_df.iloc[i]["heart1_x"]
            h1y = cleaned_df.iloc[i]["heart1_y"]
            long_axis_distance_pixel = np.sqrt((h5x - h1x)**2 + (h5y - h1y)**2)
            long_axis_distance_mm = long_axis_distance_pixel / self.PARAMS["CONVERSION RATE"]
            LAD_in_pixel.append(long_axis_distance_pixel)
            LAD_in_mm.append(long_axis_distance_mm)

            h7x = cleaned_df.iloc[i]["heart7_x"]
            h7y = cleaned_df.iloc[i]["heart7_y"]
            h3x = cleaned_df.iloc[i]["heart3_x"]
            h3y = cleaned_df.iloc[i]["heart3_y"]
            short_axis_distance_pixel = np.sqrt((h7x - h3x)**2 + (h7y - h3y)**2)
            short_axis_distance_mm = short_axis_distance_pixel / self.PARAMS["CONVERSION RATE"]
            SAD_in_pixel.append(short_axis_distance_pixel)
            SAD_in_mm.append(short_axis_distance_mm)

            Heart_Volume = 1/6 * np.pi * long_axis_distance_mm * short_axis_distance_mm**2
            Heart_Volumes_in_mm3.append(Heart_Volume)
            Heart_Volumes_in_pL.append(Heart_Volume * 10**6)

        # summary_df = pd.DataFrame()
        # summary_df["LAD_in_pixel"] = LAD_in_pixel
        # summary_df["LAD_in_mm"] = LAD_in_mm
        # summary_df["SAD_in_pixel"] = SAD_in_pixel
        # summary_df["SAD_in_mm"] = SAD_in_mm
        # summary_df["Heart_Volumes_in_mm3"] = Heart_Volumes_in_mm3
        # summary_df["Heart_Volumes_in_pL"] = Heart_Volumes_in_pL

        self.get_Heart_Volume_in_pL = Heart_Volumes_in_pL
        if get_tolerance:
            self.tolerance = np.std(Heart_Volumes_in_pL)
            logger.info(f"After calculation, overwrite given tolerance with {self.tolerance}")



    def Peak_Finder(self):

        xvalues, yvalues, maxima, minima = PeakFinder(progress_bar=None,
                                                    yvalues = self.get_Heart_Volume_in_pL, 
                                                    tolerance = self.tolerance)
        
        logger.info("Peak_Finder finished")
        
        self.df_maxima, self.df_minima = make_df(xvalues, yvalues, maxima, minima)
        logger.info("df_maxima and df_minima created")

    

    def SD_Calculator(self, based_on="maxima"):

        assert based_on in ["maxima", "minima"], "based_on must be either 'maxima' or 'minima'"

        # calculate intervals_maxima based on diff of df_maxima['X_maxima'] then convert to second by dividing to FRAMERATE
        intervals_maxima = self.df_maxima['X_maxima'].diff() / self.PARAMS["FRAME RATE"]
        intervals_maxima = intervals_maxima[1:] # remove first row because it is NaN

        # calculate intervals_minima based on diff of df_minima['X_minima'] then convert to second by dividing to FRAMERATE
        intervals_minima = self.df_minima['X_minima'].diff() / self.PARAMS["FRAME RATE"]
        intervals_minima = intervals_minima[1:] # remove first row because it is NaN

        if based_on == "maxima":
            nn_array = np.array(intervals_maxima)
        elif based_on == "minima":
            nn_array = np.array(intervals_minima)

        logger.info("Calculating SD1 and SD2")
        sd1, sd2 = SDCalculator(nn_array)

        self.sd1, self.sd2 = round(sd1, ALLOWED_DECIMALS), round(sd2, ALLOWED_DECIMALS)
        logger.info(f"SD1: {self.sd1}, SD2: {self.sd2}")


    def SD_Summary_Update(self):
        summary_path = Path(SUMMARY_PATH)
        if not summary_path.exists():
            summary_path.parent.mkdir(exist_ok=True, parents=True)
            summary_df = pd.DataFrame(columns=SUMMARY_FILE_COLUMNS)
        else:
            summary_df = pd.read_excel(summary_path)

        # Check if the current file path exists in the summary
        if self.given_path in summary_df["File Path"].values:
            # If the path exists, update the SD1 and SD2 values
            summary_df.loc[summary_df["File Path"] == self.given_path, ["SD1", "SD2"]] = [self.sd1, self.sd2]
        else:
            # If the path doesn't exist, append a new row with the SD1 and SD2 values
            new_row = {"File Path": self.given_path, "SD1": self.sd1, "SD2": self.sd2}
            # Use pd.concat to append the new row to the summary DataFrame
            summary_df = pd.concat([summary_df, pd.DataFrame([new_row])], ignore_index=True)
            logger.debug(f"New row added to summary: {new_row}")

        # Save the updated DataFrame back to the Excel file
        summary_df.to_excel(summary_path, index=False)
        logger.info(f"Summary file updated: {summary_path}")