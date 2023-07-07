ALLOWED_DECIMALS = 4
DEFAULT_VALUES = {
    "CONVERSION RATE": 2200,
    "FRAME RATE": 30,
    "TOLERANCE": 0.1,
}
EXCLUDE_FRAMES_FROM_EDGE = 10

ENTRY_NAMES_SET1 = ['CONVERSION RATE', 'FRAME RATE']
ENTRY_NAMES_SET2 = ['TOLERANCE', 'minPeakDistance', 'minMaximaValue', 'maxMaximaValue']
ENTRY_NAMES = ENTRY_NAMES_SET1 + ENTRY_NAMES_SET2

MUST_FILL = ['CONVERSION RATE', 'FRAME RATE', 'TOLERANCE']

SUMMARY_PATH = "Output/SDSummary.xlsx"

PEAKS_IMG_PATH = "Output/Peaks"