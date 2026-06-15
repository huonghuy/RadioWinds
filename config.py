import numpy as np
import os
from datetime import datetime, timedelta
#from backports.datetime_fromisoformat import MonkeyPatch
#MonkeyPatch.patch_fromisoformat()     # Hacky solution for Python 3.6 to use ISO format Strings

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
parent_dir = os.getcwd() + '/'  # The default is the RadioWinds directory

# SHAB14-V Example for EarthSHAB software. Runs main.py against the bundled
# SHAB14-V flight (GFS + APRS truth track) so the prediction can be compared to
# the real trajectory; the same flight is registered in evaluation/launches.json
# for the evaluation suite. To run a current-day prediction instead, set a recent
# forecast_start_time (cycle hour 00/06/12/18 UTC), set balloon_trajectory = None,
# and download the forecast first with `python -m EarthSHAB.saveNETCDF`.
forecast_start_time =  "2022-08-22 12:00:00" # Forecast start time, should match a downloaded forecast in the forecasts directory
start_time = datetime.fromisoformat("2022-08-22 14:22:35") # Simulation start time. The end time needs to be within the downloaded forecast
#balloon_trajectory = parent_dir + "balloon_data/SHAB14V-APRS.csv"  # Don't need this for radiowinds

# Single forecast file path. The reader (analysis.Forecast) opens
# this file regardless of whether it came from GFS or ERA5 — source is read
# from the file's `institution` global attribute. To run an ERA5-based
# simulation, point `file` at an ERA5 .nc instead.
_gfs_res = 0.25   # (deg) GFS grid resolution: 0.25, 0.5, or 1.0
_gfs_res_token = ("%.2f" % _gfs_res).replace(".", "p")   # 0.25->0p25, 0.5->0p50, 1.0->1p00
_gfs_step_hours = 3   # (h) temporal step between forecast hours (see netcdf_gfs below)
_gfs_step_token = f"{int(_gfs_step_hours)}h"             # 1->1h, 3->3h
# Cycles older than NOAA's ~9-day NOMADS live-retention window can't be fetched
# live; saveNETCDF auto-switches to the AWS archive, which writes an `_archive`-
# marked file (see saveNETCDF_archive._archive_output_path). Mirror that marker
# here so `file` below points at whatever the downloader actually produces.
_GFS_RETENTION_DAYS = 9
_oldest_live_cycle = (datetime.utcnow() - timedelta(days=_GFS_RETENTION_DAYS)).replace(
    hour=0, minute=0, second=0, microsecond=0)
_is_archive_cycle = (
    datetime.fromisoformat(forecast_start_time).replace(minute=0, second=0, microsecond=0)
    < _oldest_live_cycle
)
_archive_suffix = "_archive" if _is_archive_cycle else ""

# Filename encodes both the spatial resolution and the temporal step, e.g.
# gfs_0p25_3h_20260605_06.nc, so files of different grids/cadences don't collide.
# Past-retention cycles get an `_archive` suffix: gfs_0p25_3h_20220822_12_archive.nc.
_default_gfs_file = (
    parent_dir + "forecasts/gfs_" + _gfs_res_token + "_" + _gfs_step_token + "_"
    + forecast_start_time[0:4] + forecast_start_time[5:7] + forecast_start_time[8:10]
    + "_" + forecast_start_time[11:13] + _archive_suffix + ".nc"
)

forecast = dict(
    file = _default_gfs_file,
    forecast_start_time = forecast_start_time, # used to build the default file path above
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


parent_folder = parent_dir + 'SOUNDINGS_DATA/'

# Best to Change the analysis folders depending on which type of analsis you're doing
analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-FULL' + '/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-CALM' + '/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-FULL' + '/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-BURST' + '/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-optimized-WH/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-Complete-lon-fix/'
#analysis_folder = parent_dir + mode + '_ANALYSIS_' + type + '-BURST/'
maps_folder = parent_dir + 'MAPS/'

# ****************** OTHER STUFF *********************************

# Default is blowing to for path planning
blowing_to = True  # False (typical wind rose); True (direction balloon will drift in, opposite)
g = 9.80665


# ************************ ERA5 **********************************
combined = False
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