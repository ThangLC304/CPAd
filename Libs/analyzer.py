import numpy as np

from Libs.reader import *
from Libs.calculations import PeakFinder, SDCalculator
from Libs.utils import make_df, draw_peaks
from . import ALLOWED_DECIMALS, SUMMARY_PATH, EXCLUDE_FRAMES_FROM_EDGE

class Analyzer:

    def __init__(self, given_path, PARAMS):

        self.given_path = given_path
        self.PARAMS = PARAMS

        self.DEFAULT_GET_TOLERANCE_MODE = False

        reader = Reader(given_paths = [given_path])

        dfs_dict = reader.get_dfs_dict()
        for core_name, df in dfs_dict.items():
            dfs_dict[core_name] = self.cleaner(df)
            
        try:
            self.core_name = list(dfs_dict.keys())[0]
        except IndexError:
            logger.debug(f"dfs_dict: {dfs_dict}")
            logger.error(f"No file found in {given_path}")
            raise IndexError(f"No file found in {given_path}")
        self.cleaned_df = list(dfs_dict.values())[0]

        try:
            self.tolerance = PARAMS["TOLERANCE"]
            logger.info(f"Tolerance found in PARAMS, using value {self.tolerance}")
        except KeyError:
            self.tolerance = 0.1
            logger.info("Tolerance not found in PARAMS, probably the first time running, setting df_loader's default get_tolerance to True")
            self.DEFAULT_GET_TOLERANCE_MODE = True

        logger.debug(f"PARAMS: {PARAMS}")

        self.ENDPOINTS = {}
    
    def cleaner(self, given_df):

        excepted_columns = []
        for column in given_df.columns:
            if any([f"heart{num}" in column.lower() for num in [1, 3, 5, 7]]):
                excepted_columns.append(column)

        cleaned_df = given_df[excepted_columns]

        # change all values in cleaned_df to float
        cleaned_df = cleaned_df.astype(float)

        return cleaned_df
    

    def df_Loader(self, get_tolerance=None):

        if get_tolerance is None:
            get_tolerance = self.DEFAULT_GET_TOLERANCE_MODE

        cleaned_df = self.cleaned_df

        self.FRAMES = len(cleaned_df)

        LAD_in_pixel = []
        LAD_in_mm = []

        SAD_in_pixel = []
        SAD_in_mm = []

        Heart_Volumes_in_mm3 = []
        Heart_Volumes_in_pL = []

        for i in range(self.FRAMES):
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

        
        self.short_axis = LAD_in_mm



    def Peak_Finder(self):

        xvalues, yvalues, maxima, minima = PeakFinder(progress_bar=None,
                                                    yvalues = self.get_Heart_Volume_in_pL, 
                                                    tolerance = self.tolerance)
        
        logger.info("Peak_Finder finished")
        
        self.df_maxima, self.df_minima = make_df(xvalues, yvalues, maxima, minima)
        logger.info("df_maxima and df_minima created")

        self.finder_df_edge_excluder()
        logger.info("df_maxima and df_minima edge excluded")

        self.values_for_draw = [xvalues, yvalues, maxima, minima]

        


        return self.values_for_draw
    

    def finder_df_edge_excluder(self, exclude = EXCLUDE_FRAMES_FROM_EDGE):

        frame_threshold_lower = exclude
        frame_threshold_upper = self.FRAMES - exclude

        # Remove rows from self.df_maxima and self.df_minima that are in the first and last 10 frames
        self.df_maxima = self.df_maxima[(self.df_maxima['X_maxima'] >= frame_threshold_lower) & (self.df_maxima['X_maxima'] <= frame_threshold_upper)]
        self.df_minima = self.df_minima[(self.df_minima['X_minima'] >= frame_threshold_lower) & (self.df_minima['X_minima'] <= frame_threshold_upper)]


    def EndPoints_Calculator(self, based_on="maxima"):

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


        # Calculate EDV and ESV
        self.ENDPOINTS["Average EDV"] = self.df_maxima["Y_maxima"].mean()
        self.ENDPOINTS["Average ESV"] = self.df_minima["Y_minima"].mean()


        # Calculate Stroke Volume and related Endpoints
        first_max_FRAME = self.df_maxima["X_maxima"].values[0]
        first_min_FRAME = self.df_minima["X_minima"].values[0]

        y_maxima_list = self.df_maxima["Y_maxima"].values.tolist()
        y_minima_list = self.df_minima["Y_minima"].values.tolist()

        if first_max_FRAME > first_min_FRAME: # the ECG starts with a low peak
            y_minima_list = y_minima_list[1:]
            logger.info("the ECG starts with a low peak")
        else: # the ECG starts with a high peak
            logger.info("the ECG starts with a high peak")

        stroke_num = min(len(y_maxima_list), len(y_minima_list))

        stroke_list = []

        for num in range(stroke_num):
            stroke_list.append(y_maxima_list[num] - y_minima_list[num])

        self.ENDPOINTS["Stroke volume (pL/beat)"] = np.mean(stroke_list)
        
        self.ENDPOINTS['Heart rate (BPM)'] = round(60 / np.mean(nn_array), ALLOWED_DECIMALS)
        self.ENDPOINTS['Cardiac Output (pL/beat)'] = round(self.ENDPOINTS['Stroke volume (pL/beat)'] * self.ENDPOINTS['Heart rate (BPM)'], ALLOWED_DECIMALS)
        self.ENDPOINTS['Ejection Fraction (%)'] = round(self.ENDPOINTS['Stroke volume (pL/beat)'] / self.ENDPOINTS['Average EDV'] * 100, int(ALLOWED_DECIMALS/2))


        # Calculate Shortening Fraction
        ShortAxisMaxima = [self.short_axis[i] for i in self.df_maxima["X_maxima"].values.tolist()]
        ShortAxisMinima = [self.short_axis[i] for i in self.df_minima["X_minima"].values.tolist()]

        self.ENDPOINTS["Shortening Fraction (%)"] = (np.mean(ShortAxisMaxima) - np.mean(ShortAxisMinima)) / np.mean(ShortAxisMaxima) * 100


        # Calculate SD1 SD2
        logger.info("Calculating SD1 and SD2")
        sd1, sd2 = SDCalculator(nn_array)

        self.ENDPOINTS["SD1"] = round(sd1, ALLOWED_DECIMALS)
        self.ENDPOINTS["SD2"] = round(sd2, ALLOWED_DECIMALS)



    def EndPoints_Updater(self):

        summary_path = Path(SUMMARY_PATH)

        if summary_path.exists():
            summary_df = pd.read_excel(summary_path)
            if self.given_path in summary_df["File Path"].values:
                # If the path exists, update the SD1 and SD2 values
                summary_df.loc[summary_df["File Path"] == self.given_path, list(self.ENDPOINTS.keys())] = list(self.ENDPOINTS.values())
                logger.info(f"Updated Endpoints for {self.given_path}")
            else:
                # If the path doesn't exist, append a new row with the SD1 and SD2 values
                new_row = pd.DataFrame(data=[list(self.ENDPOINTS.values())], columns=list(self.ENDPOINTS.keys()))
                new_row.insert(0, "File Path", self.given_path)
                summary_df = pd.concat([summary_df, new_row], ignore_index=True)
                logger.info(f"Added Endpoints for {self.given_path}")
        else:
            # Make a dataframe from self.ENDPOINTS
            summary_df = pd.DataFrame(data=[list(self.ENDPOINTS.values())], columns=list(self.ENDPOINTS.keys()))
            # Add column 0 with the file path
            summary_df.insert(0, "File Path", self.given_path)
            logger.info(f"Created a new summary file for {self.given_path}")

        # Save the dataframe to the summary file
        summary_df.to_excel(summary_path, index=False)
        logger.info(f"Updated summary file at {summary_path}")




    # def SD_Summary_Update(self):
    #     summary_path = Path(SUMMARY_PATH)
    #     if not summary_path.exists():
    #         summary_path.parent.mkdir(exist_ok=True, parents=True)
    #         summary_df = pd.DataFrame(columns=SUMMARY_FILE_COLUMNS)
    #     else:
    #         summary_df = pd.read_excel(summary_path)

    #     # Check if the current file path exists in the summary
    #     if self.given_path in summary_df["File Path"].values:
    #         # If the path exists, update the SD1 and SD2 values
    #         summary_df.loc[summary_df["File Path"] == self.given_path, ["SD1", "SD2"]] = [self.sd1, self.sd2]
    #     else:
    #         # If the path doesn't exist, append a new row with the SD1 and SD2 values
    #         new_row = {"File Path": self.given_path, "SD1": self.sd1, "SD2": self.sd2}
    #         # Use pd.concat to append the new row to the summary DataFrame
    #         summary_df = pd.concat([summary_df, pd.DataFrame([new_row])], ignore_index=True)
    #         logger.debug(f"New row added to summary: {new_row}")

    #     # Save the updated DataFrame back to the Excel file
    #     summary_df.to_excel(summary_path, index=False)
    #     logger.info(f"Summary file updated: {summary_path}")


    def SavePeaks(self):

        try:
            draw_peaks(master=None, 
                    given_name=self.core_name, 
                    given_values=self.values_for_draw, 
                    mode="save")
        except Exception as e:
            logger.debug(f"Core name: {self.core_name}")
            logger.debug(f"Given path: {self.given_path}")
            logger.error("Error saving peaks")
            raise e            
        
        logger.info("Peaks saved")