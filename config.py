import numpy as np
import os
from datetime import datetime, timedelta

# ======================= Analysis Settings =======================

type = "ALT"                    # ALT or PRES
mode = "radiosonde"                   # radiosonde or era5
continent = "South_America"     # 'All' will download every continent
                                # Or you can do one at a time: North America, South America,
                                # Europe, Asia, Africa, Australia, Antarctica
                                # May run into rate limits
mapping_mode = mode           # mode or "diff"

start_year = 2023
end_year = 2023

# Permit ERA5 files that end before the configured calendar year is complete.
# The available months (including the final partial month) are exported, but no
# annual result or completion marker is created until all 12 months exist.
allow_partial_year = True

monthly_export_color = True
annual_export_color = True
dfi_mode = "chrome"  # Default is "chrome" for Windows 11 and Ubuntu, WSL2 prefers "selenium"

alt_step = 500                  # m
min_alt = 15000                     # m
max_alt = 28000 + alt_step - 1  # m  The +alt_step -1 is to include all data points above the
                                #    max - the next step size.
n_sectors = 16
speed_threshold = 4             # knots for Radiosonde, m/s for ERA5

# This pressure range is similar in altitude to 15.5 - 26 km
# for radiosonde, add an extra 1/3 to the next level?
# otherwise it will only include data that is right on 125 hpa, which varies from 
# radiosonde to radiosonde +/- about 5
min_pressure = 20 - 3
max_pressure = 125 + 13

# ======================= Parallelization =========================

# Multiprocessing can be finicky and run out of memory on Windows (it also seems slower)
# I have no memory issues on WSL or Ubuntu.
parallelize = True              # It's recommended to change logging to False if parallelize is True.
logging = False                 # Displays extra debugging and status text in the Terminal

# Number of worker processes used when parallelize=True. None => mode-dependent
num_workers = None
if num_workers is None:
    _cpu = os.cpu_count() or 1
    num_workers = min(4, _cpu) if mode == "era5" else _cpu

# ======================= Export ==================================

monthly_export_color = True
annual_export_color = True
dfi_mode = "playwright"             # Default is "playwright" for Windows 11 and Ubuntu, 
                                    # WSL2 prefers "selenium"
# ======================= Directories =============================

parent_dir = os.getcwd() + '/'  # The default is the RadioWinds directory
parent_folder = '/srv/shared/SOUNDINGS_DATA/'   # radiosonde only

# Best to Change the analysis folders depending on which type of analsis you're doing
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-Test2' + '/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-CALM' + '/'
analysis_folder = parent_dir + mode + '_ANALYSIS_'  + type + '/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-BURST' + '/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-optimized-WH/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-Complete-lon-fix/'
maps_folder = parent_dir + 'MAPS/'

# ======================= Forecast ================================

forecast = dict(
    #"""
    #This is for era5 data only. Look into unifying this process

    #"""
    # ERA5 data is stored one file per year. batchAnalysis rotates through
    # start_year..end_year, formatting this template with each year so it can
    # process multiple years' files in one run.
    #file_template = "/srv/shared/ERA5_PRES/{year}/era5_{year}_complete.nc",
    file_template = "/srv/shared/ERA5_COMP/{year}/{year}-ERA5-Complete.nc",
    #file_template = "/srv/shared/SOUNDINGS_DATA/",

    forecast_start_time = "2022-08-22 12:00:00", # used to build the default file path above
    GFSrate = 60,               # (s) After how many iterated dt steps are new wind speeds are looked up

    # Wind interpolation method used inside Forecast.wind_alt_Interpolate2:
    #   'linear_neighbors' - (default, historical) bearing+speed linearly
    #                        interpolated between the 2 nearest pressure
    #                        levels, with angle-wrap correction.
    #   'linear_full'      - np.interp on u and v independently across the
    #                        full altitude profile.
    #   'spline_full'      - scipy CubicSpline on u and v across the full
    #                        altitude profile; extrapolate=False, with
    #                        np.interp fallback when alt is outside the
    #                        profile bounds (avoids spline overshoot above
    #                        the highest pressure level).
    wind_interpolation = 'linear_full',
)

# Single-file consumers (the trajectory sim in Forecast.__init__ and the
# hovmoller plotting scripts) need one concrete path rather than a per-year
# rotation; default them to start_year's file.
forecast['file'] = forecast['file_template'].format(year=start_year)

# ======================= ERA5 ====================================
# ************************ ERA5 **********************************
combined = False #DO NOT CHANGE
era_file = "/srv/shared/FORECASTS/2023-ERA5-NORTH.nc"
#era_file = "forecasts/" + "western_hemisphere-2022-North.nc"
#era_file = "../../../../mnt/d/cds_api/" + "2023-ERA5-Complete.nc"
#era_file = "../../../../mnt/d/FORECASTS/" + "2023-ERA5-North.nc"
#era_file = "../../../../mnt/d/cds_api/" + "2022-ERA5-Complete-Mini.nc"
#era_file = "../../../../mnt/d/FORECASTS/" + "optimized_ERA5-2022-WH.nc"

# Mandatory pressure levels downloaded from ERA5  (~9.5km - 31km?)
era5_pressure_levels = np.asarray([650,600,550,500,450,400, 350, 300, 250, 225, 200, 175, 150, 125, 100, 70, 50, 30, 20, 10])
#era5_pressure_levels = np.asarray([125, 120, 115,110, 105, 100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 47.5, 45,42.5, 40, 37.5, 35, 32.5, 30 ,28, 26, 24, 22, 20]

if mode == "era5":
    speed_threshold = speed_threshold / 2.  # to roughly convert from knots to m/s since forecasts aren't in decimals

#cdo -f nc copy "2023-ERA5-NORTH.grib" "2023-ERA5-NORTH.nc"

# ======================= Other ===================================

# Default is blowing to for path planning
blowing_to = True               # False (typical wind rose); True (direction balloon will drift in, opposite)
g = 9.80665
