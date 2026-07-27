"""
Wyoming Upper Air Data Request and Analysis
==============================

This example shows how to use siphon's `simplewebswervice` support to create a query to
the Wyoming upper air archive.

Plot the wind data using EarthSHABS 3D windrose visualization.

Analyze for opposing wind pairs at varrying altitudes.
"""

from datetime import datetime
from pathlib import Path
import re

from metpy.units import units

from siphon.simplewebservice.wyoming import WyomingUpperAir
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import pandas as pd
import config


def windrose_output_path(station, date):
    """Build a filesystem-safe output path from the station and sounding date."""
    output_dir = Path("Pictures/3D-Windrose")
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_station = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(station).strip())
    timestamp = date.strftime("%Y-%m-%d-%H%M")
    return output_dir / f"{safe_station}-{timestamp}.png"


def interpolate(df, num_interpolations = 10):
    """
    Interpolate additional altitude levels between each altitude level provided in the radiosonde dataframe.  While the interpoaltions
    are linearly interpolated between 2 altitude levels,  the final dataframe will not be evenly distributed, because the radiosonde
    dataframe is not garuntee to be evenly distributed when collecting data.

    This function is mostly copied and pasted with slight variations from polar_interpolated_scatter_plot()

    Args:
    - df: A DataFrame in the Wisconsin Radisonde Dataframe format.
    - num_interpolations: Number of altitude interpolations between each altitude level (default is 10).
    """


    altitudes = df["height"].values
    wind_speeds = df["speed"].values
    wind_directions_deg = df["direction"].values  # Wind direction in degrees

    # Create empty interpolated altitudes and corresponding wind data
    interpolated_altitudes = []
    interpolated_speeds = []
    interpolated_directions_deg = []

    for i in range(len(altitudes) - 1):
        # Do some angle wrapping checks. Don't convert to meteorlogical winds, that's done in another function for plotting.
        angle1 = wind_directions_deg[i] % 360
        angle2 = wind_directions_deg[i+1] % 360
        angular_difference = abs(angle2 - angle1)

        if angular_difference > 180:
            if (angle2 > angle1):
                angle1 += 360
            else:
                angle2 += 360

        for j in range(num_interpolations + 1):
            alpha = j / num_interpolations
            interp_alt = altitudes[i] + alpha * (altitudes[i + 1] - altitudes[i])
            interp_speed = np.interp(interp_alt, [altitudes[i], altitudes[i + 1]], [wind_speeds[i], wind_speeds[i + 1]])

            interp_dir_deg = np.interp(interp_alt, [altitudes[i], altitudes[i + 1]],
                                       [angle1, angle2]) % 360  # make sure in the range (0, 360)

            interpolated_altitudes.append(interp_alt)
            interpolated_speeds.append(interp_speed)
            interpolated_directions_deg.append(interp_dir_deg)

    new_df = pd.DataFrame({'height': interpolated_altitudes, 'speed': interpolated_speeds, 'direction': interpolated_directions_deg})
    #print(new_df)
    return (new_df)


#===============================================================================

def polar_interpolated_scatter_plot(df, fig, ax, station, date, num_interpolations=1, color = "magma", size = 10, no_interpolation = False, blowing_to = True):
    """
    Create a polar scatter plot with altitude as the radius, wind direction in degrees, and a color bar for wind speed.

    Args:
    - df: A DataFrame containing wind data with columns "Altitude", "Wind Speed", and "Wind Direction" in degrees.
    - num_interpolations: Number of altitude interpolations between each altitude level (default is 20).
    """

    #df = df.drop(df[df['height'] < 10000].index)
    #df = df.drop(df[df['height'] > 25000].index)

    # Extract data from the DataFrame
    altitudes = df["height"].values
    wind_speeds = df["speed"].values
    wind_directions_deg = df["direction"].to_numpy(copy=True)

    if not blowing_to:
        wind_directions_deg = (wind_directions_deg - 180) % 360


    # Create interpolated altitudes and corresponding wind data
    interpolated_altitudes = []
    interpolated_speeds = []
    interpolated_directions_deg = []

    for i in range(len(altitudes) - 1):
        '''For notes on converting meteolorlogical winds to mathematical winds:
        http://colaweb.gmu.edu/dev/clim301/lectures/wind/wind-uv
        https://confluence.ecmwf.int/pages/viewpage.action?pageId=133262398
        https://www.eol.ucar.edu/content/wind-direction-quick-reference
        
        # Meteorological Wind Convention:
        U-winds are E-W
        V-winds are N-S
        
        A positive u-wind blows **to** the East and is known as a **"Westerly"** wind 
        A positive v-wind blows **to** the North and is known as a  **"Southerly"** wind
        
        Geographic Wind Direction Typical Convention: 
        
                         +V-WIND
                          (+)       
                           0°
                           ▲
                           N               
                           |               
          (-) 270° ◀ W ── [■] ── E ⯈ 90° (+)  +U-WIND
                           |               
                           S              
                           ▼ 
                          180°  
                          (-)

        '''
        #Calculate Meteorological Winds
        #angle1 = (270 - wind_directions_deg[i])  % 360  #convert from meteorlogical direction to math dirrection
        #angle2 = (270 - wind_directions_deg[i + 1]) % 360

        # Math Winds
        angle1 = wind_directions_deg[i]
        angle2 = wind_directions_deg[i + 1]


        angular_difference = abs(angle2-angle1)

        if angular_difference > 180:
            if (angle2 > angle1):
                angle1 += 360
            else:
                angle2 += 360

        for j in range(num_interpolations + 1):
            alpha = j / num_interpolations
            interp_alt = altitudes[i] + alpha * (altitudes[i + 1] - altitudes[i])
            interp_speed = np.interp(interp_alt, [altitudes[i], altitudes[i + 1]], [wind_speeds[i], wind_speeds[i + 1]])

            interp_dir_deg = np.interp(interp_alt, [altitudes[i], altitudes[i + 1]], [angle1, angle2]) % 360 #make sure in the range (0, 360)

            interpolated_altitudes.append(interp_alt)
            interpolated_speeds.append(interp_speed)
            interpolated_directions_deg.append(interp_dir_deg)

    # Create a scatter plot where radius is altitude, angle is wind direction (in radians), and color represents wind speed


    #print(interpolated_altitudes)


    #Switch from math winds to Meteorological Winda visually
    compass = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    tick_positions = np.deg2rad(np.arange(0, 360, 45))

    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_xticks(tick_positions, labels=compass)


    sc = ax.scatter(np.radians(interpolated_directions_deg), interpolated_altitudes, c=interpolated_speeds, cmap=color, s=10)


    if not no_interpolation:
        cbar = plt.colorbar(sc, label='Wind Speed (m/s)')

    # Set title
    if blowing_to:
        plt.title("3D Windrose (BLOWING TO) for Station " + str(station) + " on " + str(date))
    else:
        plt.title("3D Windrose (BLOWING FROM) for Station " + str(station) + " on " + str(date))

#Old Opposing Wind Method by looking around Circle
'''
def find_opposing_wind_ranges(df, threshold_speed, threshold_angle):
    """
    Find altitudes pairs with opposing winds.

    Threshold speed is currently unused

    Args:
    - df: A Wyoming Radisonde Dataframe
    - threshold_speed: Wind speed threshold for considering opposing winds.
    - threshold_angle: Maximum angle (in degrees) for two winds to be considered opposing.

    Returns:
    - A list of altitude ranges with opposing winds and their speeds.
    Each range is represented as an array (start_altitude, end_altitude, start_speed, end_speed).
    """

    #only check opposing winds for the altitude region
    df = df.drop(df[df['height'] < 10000].index)
    df = df.drop(df[df['height'] > 25000].index)

    # Initialize a list to store altitude ranges with opposing winds
    opposing_wind_ranges = []

    # Get the altitude and wind data as arrays
    altitudes = df["height"].values
    wind_speeds = df["speed"].values
    wind_directions = df["direction"].values

    # Iterate through altitude ranges
    num_altitudes = len(altitudes)
    for i in range(num_altitudes - 1):
        for j in range(i + 1, num_altitudes): #Calculate opposing pairs only in ascending order; no duplicates
        #for j in range(num_altitudes - 1): #Calculate all opposing pairs; duplicate pairs
            # Initialize variables to track opposing wind pairs in the range
            opposing_pair_found = False
            start_altitude = altitudes[i]

            speed_i = wind_speeds[i]
            direction_i = wind_directions[i]
            speed_j = wind_speeds[j]
            direction_j = wind_directions[j]

            # Calculate the absolute angular difference between the two directions
            angular_difference = abs(direction_i - direction_j)

            # Ensure that the angular difference is within the threshold
            if angular_difference <= 180 + threshold_angle and angular_difference >= 180 - threshold_angle:
                opposing_pair_found = True
                # Do not include Opposing Wind Pairs if the opposing wind at one level is too slow.  Default is 5 m/s
                print(altitudes[i], altitudes[j], wind_speeds[i], wind_speeds[j], wind_speeds[j] < threshold_speed)
                if wind_speeds[i] < threshold_speed:
                    opposing_pair_found = False

                if wind_speeds[j] < threshold_speed:
                    opposing_pair_found = False



            # If an opposing pair was found, add the range to the list
            if opposing_pair_found:
                #print("made it here 2")
                end_altitude = altitudes[j]
                opposing_wind_ranges.append((start_altitude, end_altitude, wind_speeds[i], wind_speeds[j] ))

    return opposing_wind_ranges
'''


####################################################
if __name__=="__main__":
    # Create a datetime object for the sounding and string of the station identifier.
    date = datetime(2023, 10, 25, 12)
    station = 'SBBV'

    pd.set_option("display.max_rows", None)
    # Make the request (a pandas dataframe is returned).
    df = WyomingUpperAir.request_data(date, station)

    print(df)

    # Units can then be attached to the values from the dataframe.
    height = df['height'].values * units(df.units['height'])
    pressure = df['pressure'].values * units(df.units['pressure'])
    temperature = df['temperature'].values * units(df.units['temperature'])
    dewpoint = df['dewpoint'].values * units(df.units['dewpoint'])
    u_wind = df['u_wind'].values * units(df.units['u_wind'])
    v_wind = df['v_wind'].values * units(df.units['v_wind'])

    ###############################################################3
    #MAIN

    #interpolate aditional altitudes between the radiosonde significant wind levels for higher fidelity data
    interpolated_df = df #interpolate(df, num_interpolations = 10) #an interpolation of 1 is just the standard data.


    #Plot 3D Wind Rose
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='polar')
    polar_interpolated_scatter_plot(interpolated_df, fig, ax, num_interpolations = 100, color = 'winter', blowing_to = config.blowing_to, station = station, date = date)

    #To plot the sounding datapoints on top of the interpolated plot:
    viridis = plt.get_cmap('Set1', 1) #This is jsut to get red dots
    polar_interpolated_scatter_plot(interpolated_df, fig, ax, num_interpolations = 1, color = viridis, size = 20, no_interpolation = True, blowing_to = config.blowing_to, station = station, date = date)


    '''
    #Calculate Opposing Wind Pairs
    threshold_speed = 5  # Threshold wind speed (m/s)
    threshold_angle = 10  # Threshold angle (degrees)

    opposing_ranges = find_opposing_wind_ranges(interpolated_df, threshold_speed, threshold_angle)

    if len(opposing_ranges) > 0:
        print("Altitude ranges with opposing winds:")
        for range_pair in opposing_ranges:
            print(f"Start Alt: {range_pair[0]} m, End Alt: {range_pair[1]} m, Start Speed: {range_pair[2]} m/s, End Speed: {range_pair[3]} m/s" )
    else:
        print("No altitude ranges with opposing winds found.")

    opposing_ranges = np.array(opposing_ranges)
    print("Number of Altitude Levels", len(df["height"]))
    print("Number of Opposing Wind Pairs", len(opposing_ranges))

    print()
    '''

    '''
    #Plot Opposing wind Pairs
    fig = plt.figure(figsize=(10, 8))
    plt.scatter(opposing_ranges[:, 0], opposing_ranges[:, 1])
    plt.xlabel("Lower Bound Altitude Pair")
    plt.ylabel("Upper Bound Altitude Pair")
    '''

    output_path = windrose_output_path(station, date)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    print("Saved windrose to " + str(output_path))

    plt.show()
