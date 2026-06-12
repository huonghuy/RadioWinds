
from geographiclib.geodesic import Geodesic
import numpy as np
import netCDF4
from termcolor import colored
import xarray as xr
import pandas as pd
import matplotlib.cm as cm
import matplotlib.pyplot as plt
from analysis import opposing_wind_wyoming
import config
from plotting.plot3DWindrose import polar_interpolated_scatter_plot
import windrose
import sys

class ERA5:
    def __init__(self):
        self.geod = Geodesic.WGS84

    def import_forecast(self, filepath):
        self.file = netCDF4.Dataset(filepath)

        self.ds = xr.open_dataset(filepath, engine="netcdf4", decode_times=True)
        print(self.ds)
        #dfgdfg

        # Safely check if 'plev' exists in the netCDF4 dataset
        if hasattr(self.file, 'variables') and 'plev' in self.file.variables or hasattr(self.file,
                                                                                        'dims') and 'plev' in self.file.dims:
            print("FIXING LON")
            self.ds = self.ds.assign_coords(lon=((self.ds.lon + 180) % 360) - 180).sortby("lon")
            print(self.ds)
        else:
            print("'plev' is not found in the dataset!")

        #print(self.ds)
        #

    def get_statistics(self):
        #print(self.file)

        # Safely check for the presence of 'plev' coordinate and set variable names accordingly
        if hasattr(self.file, 'variables') and 'plev' in self.file.variables or hasattr(self.file,
                                                                                        'dims') and 'plev' in self.file.dims:
            lat_var = "lat"
            lon_var = "lon"
        else:
            lat_var = "latitude"
            lon_var = "longitude"

        time_arr = self.file.variables['time']
        # Convert from epoch to human readable time. Different than GFS for now.
        self.time_convert = netCDF4.num2date(time_arr[:], time_arr.units, time_arr.calendar)

        netcdf_ranges = self.file.variables['u'][0, :, :, :]
        self.determineRanges(netcdf_ranges)

        # smaller array of downloaded forecast subset
        self.lat = self.file.variables[lat_var][self.lat_max_idx:self.lat_min_idx]
        self.lon = self.file.variables[lon_var][self.lon_min_idx:self.lon_max_idx]

        # min/max lat/lon degree values from netcdf4 subset
        self.LAT_LOW = self.file.variables[lat_var][self.lat_min_idx - 1]
        self.LON_LOW = self.file.variables[lon_var][self.lon_min_idx]
        self.LAT_HIGH = self.file.variables[lat_var][self.lat_max_idx]
        self.LON_HIGH = self.file.variables[lon_var][self.lon_max_idx - 1]

        print()
        print("ERA5 Forecast Statistics")
        print("LAT RANGE: min: " + str(self.file.variables[lat_var][self.lat_min_idx - 1]),
              " max: " + str(self.file.variables[lat_var][self.lat_max_idx]) + " size: " + str(
                  self.lat_min_idx - self.lat_max_idx))
        print("LON RANGE: min: " + str(self.file.variables[lat_var][self.lon_min_idx]),
              " max: " + str(self.file.variables[lon_var][self.lon_max_idx - 1]) + " size: " + str(
                  self.lon_max_idx - self.lon_min_idx))


        start_datetime = self.time_convert[self.start_time_idx]
        end_datetime = self.time_convert[self.end_time_idx]

        print("TIME RANGE: start time: " + str(self.time_convert[self.start_time_idx]) +
                                " end time: " + str(self.time_convert[self.end_time_idx]))
        print()

        return start_datetime, end_datetime

    def determineRanges(self, netcdf_ranges):
        """
        Determine the dimensions of actual data. If you have columns or rows with missing data
        as indicated by NaN, then this function will return your actual shape size so you can
        resize your data being used.

        """

        print(netcdf_ranges.shape)
        results = np.all(~netcdf_ranges.mask)
        if results == False:
            timerange, latrange, lonrange = np.nonzero(~netcdf_ranges.mask)

            self.start_time_idx = timerange.min()
            self.end_time_idx = timerange.max()
            self.lat_min_idx = latrange.min()  # Min/Max are switched compared to with ERA5
            self.lat_max_idx = latrange.max()
            self.lon_min_idx = lonrange.min()
            self.lon_max_idx = lonrange.max()
        else:  # Typically this for ERA5 because they don't mask data, right?
            self.start_time_idx = 0
            self.end_time_idx = len(self.time_convert) - 1
            if config.combined:
                levelsi, lati, loni = netcdf_ranges.shape
            else:
                lati, loni = netcdf_ranges.shape
            # THese are backwards???
            self.lat_min_idx = lati
            self.lat_max_idx = 0
            self.lon_max_idx = loni
            self.lon_min_idx = 0

    def get_station(self, time, lat, lon):
        t = pd.to_datetime(time)
        tmin, tmax = pd.to_datetime(self.ds.time.min().values), pd.to_datetime(self.ds.time.max().values)
        if not (tmin <= t <= tmax):
            raise ValueError(f"{t} is outside file range {tmin}–{tmax}")
        if hasattr(self.file, 'variables') and 'plev' in self.file.variables or hasattr(self.file,
                                                                                        'dims') and 'plev' in self.file.dims:
            station_ds = self.ds.sel(time=time, lon=lon, lat=lat, method="nearest")
        else:
            station_ds = self.ds.sel(time=time, longitude=lon, latitude=lat, method="nearest")


        station_df = self.get_dataframe(station_ds, time)


        return station_df

    def get_dataframe(self, station, time):
        #print(station)
        g = 9.80665  # gravitation constant used to convert geopotential height to height
        df = pd.DataFrame()

        df['height'] = station.z / g
        df['time'] = pd.to_datetime(station.time.values)
        df['u_wind'] = station.u * 1  # put in same as radiosonde format,  blowing from?
        df['v_wind'] = station.v * 1  # put in same as radiosonde format,  blowing from?
        df['speed'] = (df['u_wind'] ** 2 + df['v_wind'] ** 2) ** 0.5
        df['direction'] = (90 - np.rad2deg(np.arctan2(df['v_wind'], df['u_wind']))) % 360  # convert to meteolorological wind?
        if hasattr(self.file, 'variables') and 'plev' in self.file.variables or hasattr(self.file,
                                                                                        'dims') and 'plev' in self.file.dims:
            df['pressure'] = station.plev/100 # Need to convert from Pa to hPa for full CDS API

        else:
            df['pressure'] = station.level

        #Reverse order, so altitude is in ascending order
        df = df[::-1].reset_index(drop=True)
        return df

# An Example
if __name__=="__main__":
    time = date = '2023-01-01  00:00:00'

    #PHTO
    lat = 19.72 #between    0 ->  70
    lon = -155  #between -180 -> -45

    era5 = ERA5()
    #era5.import_forecast("forecasts/" + "western_hemisphere-08-08-23.nc")
    era5.import_forecast(config.era_file)
    era5.get_statistics()

    df = era5.get_station(time, lat, lon)

    print(df)
    #print("hey')")

    #sdfs

    #if config.altitude_type == "pres":
    #    df['height'] = df.index


    station = 'test'

    min_alt = config.min_alt
    max_alt = config.max_alt
    min_pressure = config.min_pressure
    max_pressure = config.max_pressure
    alt_step = config.alt_step
    n_sectors = config.n_sectors
    speed_threshold = config.speed_threshold


    print()
    print()

    # PLOTTING BEFORE FILTERING)
    if not config.blowing_to:
        df['direction'] = (df['direction'] - 180) % 360

        # ================= Filter Data Frame for Opposing WInd Analysis ===================

    if config.type == 'ALT':
        df = df.drop(df[df['height'] < min_alt].index)
        df = df.drop(df[df['height'] > max_alt].index)
        # df = df.drop(df[df['speed'] < 2].index) #we'll ad this in later on'
    else:
        df = df.drop(df[df['pressure'] < min_pressure].index)
        df = df.drop(df[df['pressure'] > max_pressure].index)
        # df = df [::-1]

    if config.type == 'PRES':
        wind_bins = config.era5_pressure_levels[::-1]
        wind_bins = wind_bins[(wind_bins <= config.max_pressure)]
        wind_bins = wind_bins[(wind_bins >= config.min_pressure)]
        print(wind_bins)
    else:
        wind_bins = np.arange(min_alt, max_alt, alt_step)

    df.dropna(inplace=True)
    ws = np.asarray(df['speed'])
    wd = np.asarray(df['direction'])
    alt = np.asarray(df['height'])

    #print(df)

    # ============= Unfiltered Standard Windspeed Windrose ======================
    df.dropna(inplace=True)
    ws = np.asarray(df['speed'])
    wd = np.asarray(df['direction'])
    alt = np.asarray(df['height'])
    pressure = np.asarray(df['pressure'])

    ax2 = windrose.WindroseAxes.from_ax()
    ax2.bar(wd, ws, opening=.8, bins=np.arange(0, 50, 5), nsector=n_sectors, cmap=cm.cool_r)
    ax2.set_legend()

    if config.blowing_to: #ERA4 is flipped from Radiosonde
        ax2.set_title("Speed Windrose (BLOWING TO) for Station " + str(station) + " on " + str(date))
    else:
        ax2.set_title("Speed Windrose (BLOWING FROM) for Station " + str(station) + " on " + str(date))

    #Determine Wind Statistics
    opposing_wind_directions, opposing_wind_levels = opposing_wind_wyoming.determine_opposing_winds(df, wind_bins = wind_bins, n_sectors = n_sectors, speed_threshold = speed_threshold)
    calm_winds = opposing_wind_wyoming.determine_calm_winds(df, alt_step = alt_step)
    full_winds = opposing_wind_wyoming.determine_full_winds(df, wind_bins = wind_bins, speed_threshold = speed_threshold)

    print()
    print(df)

    print("WIND STATISTICS")
    if not calm_winds.any() and not opposing_wind_levels.any():
        print(colored("Wind Diversity FAIL.", "red"))
    else:
        if not calm_winds.any():
            print(colored("No Calm Winds.", "yellow"))
        else:
            print(colored("Calm Winds.", "green"))

        if not opposing_wind_levels.any():
            print(colored("No Opposing Winds.", "yellow"))
        else:
            print(colored("Opposing Winds.", "green"))

        if not full_winds:
            print(colored("No Full Wind Diversity.", "yellow"))
        else:
            print(colored("Full Wind Diversity", "green"))


    print()
    print("Calm Winds Regions:", calm_winds)
    print("Opposing Wind Levels:", opposing_wind_levels)


    ### PLOTING AFTER FILTERING###
    #asfa
    ws = np.asarray(df['speed'])
    wd = np.asarray(df['direction'])
    #wd = wd * blowing % 360
    alt = np.asarray(df['height'])

    #Altitude Windrose
    ax = windrose.WindroseAxes.from_ax()
    if config.type == 'ALT':
        ax.bar(wd, alt, opening=1, bins=wind_bins, nsector=n_sectors, cmap=cm.rainbow)
    else:
        ax.bar(wd, pressure, opening=1, bins=wind_bins, nsector=n_sectors, cmap=cm.rainbow)
    ax.set_legend(loc = 'lower left')

    if config.blowing_to: #ERA5 is flipped from radiosonde (already default to blowing to)
        ax.set_title("Altitude Windrose (BLOWING TO) for Station " +str(station) + " on " + str(date))
    else:
        ax.set_title("Altitude Windrose (BLOWING FROM) for Station " + str(station) + " on " + str(date))

    # Plot 3D Wind Rose
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='polar')
    polar_interpolated_scatter_plot(df, fig, ax, num_interpolations=100, color='winter', blowing_to = config.blowing_to,
                                    station=station, date=date)

    # To plot the sounding datapoints on top of the interpolated plot:
    viridis = cm.get_cmap('Set1', 1)  # This is just to get red dots
    polar_interpolated_scatter_plot(df, fig, ax, num_interpolations=1, color=viridis, size=20,
                                    no_interpolation=True, blowing_to = config.blowing_to, station=station, date=date)

    plt.figure()

    plt.plot(df['u_wind'],df['height'])
    plt.plot(df['v_wind'],df['height'])

    plt.show()
