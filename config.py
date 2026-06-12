import numpy as np
import os

# **************** DOWNLOAD AND ANALYSIS ************************

type = "ALT"                    # ALT or PRES
mode = "era5"             # radiosonde or era5
continent = "North_America"               # 'all' will download every continent
                                # Or you can do one at a time N: orth America, South America, 
                                # Europe, Asia, Africa, Australia, Antarctica
                                # May run into rate limits
mapping_mode = "diff"           # mode or diff

# Multithreading can be finicky and run out of memory on Windows (it also seems slower)
# I have no memory issues on WSL or Ubuntu.
parallelize = True #True         # It's recommended to change logging to False if parallelize is True.
logging = False                  # Displays extra debugging and status text in the Terminal

start_year = 2025
end_year = 2025

monthly_export_color = True
monthly_export_color = True
annual_export_color = True
dfi_mode = "chrome"  # Default is "chrome" for Windows 11 and Ubuntu, WSL2 prefers "selenium"

alt_step = 500                  # m
min_alt = 0               # m
max_alt = 28000 + alt_step-1    # m  The +alt_step -1 is to include all data points above the max - the next step size.
n_sectors = 16                  # m
speed_threshold = 4             # knots for Radiosonde,  m/s for ERA5

# This pressure range is similar in altitude to 15.5 - 26 km
# for radiosonde, add an extra 1/3 to the next level?
# otherwise it will only include data that is right on 125 hpa,  which varies from radiosonde to radiosonde +/- about 5
min_pressure = 20  - 3
max_pressure = 125 + 13

# ******************** DIRECTORY SETUP **************************

base_directory = os.getcwd() + '/'  # The default is the RadioWinds directory
parent_folder = base_directory + 'SOUNDINGS_DATA/'

# Best to Change the analysis folders depending on which type of analsis you're doing
analysis_folder = base_directory + mode + '_ANALYSIS_' + type + '-FULL' + '/'
#analysis_folder = base_directory + mode + '_ANALYSIS_' + type + '-CALM' + '/'
#analysis_folder = base_directory + mode + '_ANALYSIS_' + type + '-FULL' + '/'
#analysis_folder = base_directory + mode + '_ANALYSIS_' + type + '-BURST' + '/'
#analysis_folder = base_directory + mode + '_ANALYSIS_' + type + '-optimized-WH/'
#analysis_folder = base_directory + mode + '_ANALYSIS_' + type + '-Complete-lon-fix/'
#analysis_folder = base_directory + mode + '_ANALYSIS_' + type + '-BURST/'
maps_folder = base_directory + 'MAPS/'

# ****************** OTHER STUFF *********************************

# Default is blowing to for path planning
blowing_to = True  # False (typical wind rose); True (direction balloon will drift in, opposite)
g = 9.80665


# ************************ ERA5 **********************************
combined = True
era_file = f"/srv/shared/ERA5_PRES/{start_year}/era5_{start_year}_complete.nc"
#era_file = "forecasts/" + "western_hemisphere-2022-North.nc"
#era_file = "../../../../mnt/d/cds_api/" + "2023-ERA5-Complete.nc"
#era_file = "../../../../mnt/d/FORECASTS/" + "2023-ERA5-North.nc"
#era_file = "../../../../mnt/d/cds_api/" + "2022-ERA5-Complete-Mini.nc"
#era_file = "../../../../mnt/d/FORECASTS/" + "optimized_ERA5-2022-WH.nc"

# Mandatory pressure levels downloaded from ERA5  (~9.5km - 31km?)
era5_pressure_levels = np.asarray([300, 250, 225, 200, 175, 150, 125, 100, 70, 50,  30,  20, 10])
#era5_pressure_levels = np.asarray([125, 120, 115,110, 105, 100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 47.5, 45,42.5, 40, 37.5, 35, 32.5, 30 ,28, 26, 24, 22, 20]
if mode == "era5":
    speed_threshold = speed_threshold / 2.  # to roughly convert from knots to m/s since forecasts aren't in decimals

#cdo -f nc copy "2023-ERA5-NORTH.grib" "2023-ERA5-NORTH.nc"