from datetime import datetime
from siphon.simplewebservice.wyoming import WyomingUpperAir
import pandas as pd
from termcolor import colored
import windrose
import numpy as np
import matplotlib.pyplot as plt
import sys
from matplotlib import colormaps
import matplotlib.cm as cm
from plotting.plot3DWindrose import polar_interpolated_scatter_plot
import config

"""
This script determines the wind diversity statistics for one radiosonde launch. THey are classified under 4 categories.

Fail :                            No Opposing Winds or Calm Winds
Calm Wind Station Keeping:        There is a region with winds under speed threshold (default is 1 m/s)
Opposing Wind Station Keeping:    There is a region with opposing winds
Full Winds Station Keeping:       There are 4 quadrants with opposing winds for full navigation

The main function downloads a radiosonde from UofWy, determines the statistics, and provides some additional plots.

The configurable config parameters that this script relies on are:

* **type** : To analyze wind diversity via ALT or PRES (default is ALT for radiosonde, and PRES for ERA5)
* **alt_step** : The altitude step size for wind binning via ALT
* **min_alt**  : the minimum altitude for wind binning via ALT
* **max_alt** : the maximum altitude for wind binning
* **n_sectors** : How many sectors to check for opposing or full winds is (Default is 16 for opposing and 8 for full)
* **speed_threshold** : The minimum speed of winds to analyze,  anything below this level is considered calm winds
* **min_pressure** : the minimum pressure for wind binning via PRES
* **max_pressure** : the maximum pressure for wind binning via PRES

.. note:

    WMO is a 5 digit unique identifier and consistent between different data sources.
    WBAN is a U.S. only 5 digit unique identifier. I'm not sure if it is consistent with WMO.
    I suggest we use WMO because it includes U.S. + International.

    University of Wyoming uses FAA Airport Codes (no K) and WMO

    RAOBS uses FAA Airport Codes (no K) and WMO

    IGRA2 uses WMO

    # Use WMO code or Airport Abbreviation/Nickname. Abbreviation is not consistent between UWY, IGRA2, and RAOBS but WMO code is.

    Additional References:
    https://rucsoundings.noaa.gov/raob.short
    https://www1.ncdc.noaa.gov/pub/data/igra/igra2-station-list.txt
    https://artefacts.ceda.ac.uk/badc_datadocs/radiosglobe/stations_sorting_lists/stnlist-historical.html
    Also see emails from Larry Oolman and Joshua Webber

"""


def determine_calm_winds(df, speed_threshold=4, alt_step=500):
    """
        Determine altitude levels with calm winds (withing speed threshold) for an individual sounding.

        Returns a list of altitudes rounded to nearest alt_step size where calm winds were recorded.
        Because of how the windrose histogram works...
        This is why max alt in config should be max_alt + alt_step -1  instead of max_alt + alt_step/2

        :param speed_threshold: wind speed threshold for calm winds [Default is <=4 knots)
        :type speed_threshold: float
        :param alt_step: altitude step size to round heights to. Only for when by_pressure is false
        :type alt_step: boolean
        :returns: array of altitudes (rounded to nears alt_step) where there are calm winds (winds < speed threshold)
        :rtype: [int]
    """

    calm_winds = df[df['speed'] <= speed_threshold]
    calm_winds = calm_winds.copy()  # this is needed to get rid of the SettingWithCopyWarning

    if config.type == "ALT":
        # Round calm wind regions to nearest alt_Step size (probably either 500 or 1000 m)
        calm_winds['height'] = calm_winds.height.apply(lambda x: round(x/ alt_step) * alt_step)
        return np.unique(calm_winds['height'].to_numpy())  # remove duplicate calm wind regions and return the array

    if config.type == "PRES":
        # This does not split into bins for radiosondes right now, but it does for ERA5,
        # which is already split into the proper bins
        return np.unique(calm_winds['pressure'].to_numpy())  # remove duplicate calm wind regions and return the array


def determine_opposing_winds(df, wind_bins, n_sectors, speed_threshold = 4):
    """
        Determine altitude levels with opposing winds for an individual sounding.

        The wind directions are broken into wind-bins and n_sectors

        n-sectors is the amount of

        :param wind_bins: How data is seperated for histogram,  should be either speed or altitude
        :type wind_bins: array[float]
        :param n_sectors: How data is seperated for histogram,  should be either speed or altitude
        :type n_sectors: int (even number)
        :returns:
        :rtype:
    """

    df = df.drop(df[df['speed'] < speed_threshold].index)
    wd = np.asarray(df['direction'])
    alt = np.asarray(df['height'])
    pressure = np.asarray(df['pressure'])

    # Generate a histogram with wind directions and altitudes using windrose.historgram
    # I think the histogram works by including current_step up to next step,
    # rather than +/-  step/2
    if config.type == "ALT":
        dir_edges, var_bins, table = windrose.windrose.histogram(wd, alt, bins=wind_bins, nsector=n_sectors)
    if config.type == "PRES":
        dir_edges, var_bins, table = windrose.windrose.histogram(wd, pressure, bins=wind_bins, nsector=n_sectors)


    #print(table)
    #sdfsRsdf
    #Determine the sectors (directions) that contain non zero values (altitude levels that have wind)
    df = pd.DataFrame(table)


    altitude_lookup_idxs = df.apply(np.flatnonzero, axis=0) # altitude can be pressure or height, depending on by_pressure variable


    #print(df)
    #print(wind_bins)
    #print(altitude_lookup_idxs)
    #print(np.sum(table,axis=0))
    #sdfs


    opposing_wind_levels = np.array([])
    opposing_wind_directions = np.array([])

    # Determine the sectors that have opposing winds by checking the current index and the complimentary index at n_sectors/2.
    # Also determine the altitudes contains in the opposing wind pairs for calculating probabilities later.
    for i in range (0,int(n_sectors/2)):
        # check if opposing sectors in the histogram tables have values greater than 0
        # (therefore, there are winds in that sectors)
        if np.sum(table, axis=0)[i] != 0 and np.sum(table, axis=0)[i+int(n_sectors/2)] != 0:
            for idx in altitude_lookup_idxs[i]:
                opposing_wind_levels = np.append(opposing_wind_levels, var_bins[idx])
                #print(var_bins[idx])
                opposing_wind_directions = np.append(opposing_wind_directions, i)
            for idx in altitude_lookup_idxs[i+int(n_sectors/2)]:
                #print(var_bins[idx])
                opposing_wind_levels = np.append(opposing_wind_levels, var_bins[idx])
                opposing_wind_directions = np.append(opposing_wind_directions, i+int(n_sectors/2))

    # sort the opposing wind altitudes and direction idxs (format later) in ascending order and remove duplicates
    opposing_wind_levels = np.sort(np.unique(opposing_wind_levels))
    opposing_wind_directions = np.sort(np.unique(opposing_wind_directions))

    #print(opposing_wind_levels)

    return opposing_wind_directions, opposing_wind_levels


def getNumofSectors(table):
    """
        Takes a 2D histogram table and calculates how many sectors have wind data in the altitude region of interest.

    """
    sector_count = 0
    for i in range(0,len(table[0])):
        column_sum = np.sum(table, axis=0)[i]
        #print(row_sum)
        if column_sum >= 1:
            sector_count += 1

    #print("sector_count", sector_count)

    return sector_count



def determine_full_winds_new(df, wind_bins, speed_threshold=config.speed_threshold, by_pressure=False):
    df = df.drop(df[df['speed'] < speed_threshold].index)

    wd = np.asarray(df['direction'])
    alt = np.asarray(df['height'])
    pressure = np.asarray(df['pressure'])

    if config.type == "ALT":
        dir_edges, var_bins, table = windrose.windrose.histogram(wd, alt, bins=wind_bins, nsector=16)
    if config.type == "PRES":
        dir_edges, var_bins, table = windrose.windrose.histogram(wd, pressure, bins=wind_bins, nsector=16)

    sector_count = getNumofSectors(table)

    return sector_count


def determine_full_winds(df, wind_bins, speed_threshold=2, by_pressure=False):
    """
        This function determines if an individual sounding has full navigation possibility in the filtered region.

        The winds are distributed into 8 sectors. Then we check if N-E-S-W or NE-SE-SW-NW have winds in every quadrant.
        If so, then "full navigation" is possible.

        :param wind_bins: How data is seperated for histogram,  should be either speed or altitude
        :type wind_bins: array[float]
        :param speed_threshold:  Minimum wind speed to consider for analysis
        :type speed_threshold: float
        :returns: full_winds
        :rtype: boolean
    """

    df = df.drop(df[df['speed'] < speed_threshold].index)

    wd = np.asarray(df['direction'])
    alt = np.asarray(df['height'])
    pressure = np.asarray(df['pressure'])

    if config.type == "ALT":
        dir_edges, var_bins, table = windrose.windrose.histogram(wd, alt, bins=wind_bins, nsector=8)
    if config.type == "PRES":
        dir_edges, var_bins, table = windrose.windrose.histogram(wd, pressure, bins=wind_bins, nsector=8)

    full_winds = False

    # check if N-E-S-W or NE-SE-SW-NW have winds in every quadrant. If so, then "full navigation" is possible.
    if np.sum(table, axis=0)[0] != 0 and np.sum(table, axis=0)[2] != 0 and \
            np.sum(table, axis=0)[4] != 0 and np.sum(table, axis=0)[6] != 0:
        full_winds = True
    if np.sum(table, axis=0)[1] != 0 and np.sum(table, axis=0)[3] != 0 and \
            np.sum(table, axis=0)[5] != 0 and np.sum(table, axis=0)[7] != 0:
        full_winds = True

    return full_winds


def print_wind_statistics(opposing_wind_directions, opposing_wind_levels, calm_winds, full_winds):
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

# =======================================================================================
# Below shows and example of getting wind statistics for Hilo Hawaii
# and generates several plots
# =======================================================================================


if __name__ == "__main__":
    # Download Individual radiosonde Sounding from University of Wyoming.
    date = datetime(2023, 5, 27, 12)
    station = 'SBBV'

    print(station, date)

    # Make the request (a pandas dataframe is returned).
    # If 503 Error, server to busy -> run script again until it works.
    # The script will only work if there's no data for that day, but that's a different error
    try:
        df = WyomingUpperAir.request_data(date, station)
    except ValueError as ve:
        print(colored(ve,"red"))
        sys.exit()

    # Default values for individual sounding data filtering
    min_alt = config.min_alt
    max_alt = config.max_alt
    min_pressure = config.min_pressure
    max_pressure = config.max_pressure
    alt_step = config.alt_step
    n_sectors = config.n_sectors
    speed_threshold = config.speed_threshold

    # Radiosondes are Blowing from by default
    if config.blowing_to:
        df['direction'] = (df['direction'] - 180) % 360

    # ============= Unfiltered Standard Windspeed Windrose ======================
    df.dropna(inplace=True)
    ws = np.asarray(df['speed'])
    wd = np.asarray(df['direction'])
    alt = np.asarray(df['height'])
    pressure = np.asarray(df['pressure'])

    #print(ws)

    ax2 = windrose.WindroseAxes.from_ax()
    ax2.bar(wd, ws, opening=.8, bins=np.arange(0, 50, 5), nsector=n_sectors, cmap=cm.cool_r)
    ax2.set_legend()

    if config.blowing_to:
        ax2.set_title("Speed Windrose (BLOWING TO) for Station " + str(station) + " on " + str(date))
    else:
        ax2.set_title("Speed Windrose (BLOWING FROM) for Station " + str(station) + " on " + str(date))

    # ================= Filter Data Frame for Opposing Wind Analysis ===================

    if config.type == "ALT":
        df = df.drop(df[df['height'] < min_alt].index)
        df = df.drop(df[df['height'] > max_alt].index)
        # df = df.drop(df[df['speed'] < 2].index) # we'll add this in later on'
    if config.type == "PRES":
        df = df.drop(df[df['pressure'] < min_pressure].index)
        df = df.drop(df[df['pressure'] > max_pressure].index)
        # df = df [::-1]

    if config.type == "PRES":
        wind_bins = config.era5_pressure_levels[::-1]
        wind_bins = wind_bins[(wind_bins <= config.max_pressure)]
        wind_bins = wind_bins[(wind_bins >= config.min_pressure)]
        if config.logging:
            print(wind_bins)
    if config.type == "ALT":
        wind_bins = np.arange(min_alt, max_alt + alt_step, alt_step)

    ws = np.asarray(df['speed'])
    wd = np.asarray(df['direction'])
    alt = np.asarray(df['height'])
    pressure = np.asarray(df['pressure'])

    # Determine Wind Statistics
    opposing_wind_directions, opposing_wind_levels = determine_opposing_winds(df, wind_bins=wind_bins,
                                                                              n_sectors=n_sectors,
                                                                              speed_threshold=speed_threshold)
    calm_winds = determine_calm_winds(df, alt_step=alt_step)
    full_winds = determine_full_winds(df, wind_bins=wind_bins, speed_threshold=speed_threshold)

    if config.logging:
        print("WIND STATISTICS:")
        print_wind_statistics(opposing_wind_directions, opposing_wind_levels, calm_winds, full_winds)
        print()
        print("Calm Winds Regions:", calm_winds)
        print("Opposing Wind Levels:", opposing_wind_levels)

        # PLOTTING AFTER FILTERING
        #print(df)
        #print(alt)

    # Altitude Windrose
    ax = windrose.WindroseAxes.from_ax()
    if config.type == "ALT":
        ax.bar(wd, alt, opening=1, bins=wind_bins, nsector=n_sectors, cmap=cm.rainbow)
    if config.type == "PRES":
        ax.bar(wd, pressure, opening=1, bins=wind_bins, nsector=n_sectors, cmap=cm.rainbow)
    ax.set_legend(loc='lower left')

    if config.blowing_to:
        ax.set_title("Altitude Windrose (BLOWING TO) for Station " +str(station) + " on " + str(date))
    else:
        ax.set_title("Altitude Windrose (BLOWING FROM) for Station " + str(station) + " on " + str(date))

    # Plot 3D Wind Rose
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='polar')
    polar_interpolated_scatter_plot(df, fig, ax, num_interpolations=100, color='winter', blowing_to=config.blowing_to,
                                    station=station, date=date)

    # To plot the sounding datapoints on top of the interpolated plot:
    red_dots = colormaps["Set1"].resampled(1)
    polar_interpolated_scatter_plot(df, fig, ax, num_interpolations=1, color=red_dots, size=20,
                                    no_interpolation=True, blowing_to=config.blowing_to, station=station, date=date)

    plt.figure()
    plt.plot(df['u_wind'], df['height'])
    plt.plot(df['v_wind'], df['height'])

    plt.show()
