"""
Generates Figures 1 and A1 in the manuscript"""

from os import listdir
import pandas as pd
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator,  DateFormatter
import os
import xarray as xr



import sys
sys.path.append(os.path.dirname(os.path.abspath('/mnt/d/RadioWinds/config.py')))

import config
import utils

# Handling missing data: Replace missing days with NaN values in the DataFrame
def handle_missing_data(df):
    """
    Identify consecutive missing data and ensure they appear as blank regions in the plot.
    """
    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
    df = df.reindex(full_index)  # Reindex to ensure all days are included, even those with no data
    return df

    #return df.dropna(how='all')

FAA = "SBBV"
WMO = utils.lookupWMO(FAA)
Station_Name = utils.lookupStationName(FAA)
CO = utils.lookupCountry(FAA)
lat,lon,el = utils.lookupCoordinate(FAA)
print(WMO, FAA, Station_Name, lat,lon,el)

wind_bins = np.arange(config.min_alt-500, config.max_alt, config.alt_step)
labels = np.arange(config.min_alt, config.max_alt, config.alt_step)
wind_directions = pd.DataFrame(columns=labels)



def getDecadalMonthlyMeans(FAA, WMO):
    for year in range (config.start_year, config.end_year +1):
        for month in range (1,13):
            suffix = str(month) + "/"


            analysis_folder = utils.get_data_folder(FAA, WMO, year) +suffix
            files = [f for f in listdir(analysis_folder) if f.endswith(".csv")]
            #print(files)
            for file in files:
                print(file)

                df = pd.read_csv(analysis_folder + file, index_col=0)

                if config.type == "ALT":
                    df.dropna(subset=['height'], how='all', inplace=True)
                    df = df.drop(df[df['height'] < config.min_alt].index)
                    df = df.drop(df[df['height'] > config.max_alt].index)

                df['wind_bin'] = pd.cut(df['height'], wind_bins+501, labels = labels)

                #print(df)

                #df = pd.to_numeric(df, errors='coerce')
                directions = df.groupby('wind_bin', observed=False)['direction'].mean()
                directions = directions.interpolate(method='nearest')

                #print(directions)


                date_chunks = file[:-4].split('-')
                #time = datetime(config.start_year, int(date_chunks[2]), int(date_chunks[3]), int(date_chunks[4]), 0, 0)
                time = datetime(int(date_chunks[1]), int(date_chunks[2]), int(date_chunks[3]), int(date_chunks[4]), 0, 0)
                #Accounts for year
                wind_directions.loc[time, :] = directions

                #print(wind_directions)

                #asfa

                #wind_directions = wind_directions.sort_values(by=wind_directions.index)

    return(wind_directions)


decadal_df = getDecadalMonthlyMeans(FAA, WMO)
print(decadal_df)


decadal_df = decadal_df.sort_index()

decadal_df.index = pd.to_datetime(decadal_df.index)

# Handle missing data to avoid filling in colors
#decadal_df = handle_missing_data(decadal_df)

#SBBV 2023
#'''
#decadal_df.loc[pd.to_datetime("2023-02-04 12:00:00")] = np.nan
#decadal_df.loc[pd.to_datetime("2023-06-26 12:00:00")] = np.nan
#'''

#SCSN
'''
decadal_df.loc[pd.to_datetime("2023-04-03 12:00:00")] = np.nan
decadal_df.loc[pd.to_datetime("2023-04-07 12:00:00")] = np.nan
decadal_df.loc[pd.to_datetime("2023-09-28 12:00:00")] = np.nan
decadal_df.loc[pd.to_datetime("2023-09-30 12:00:00")] = np.nan
decadal_df.loc[pd.to_datetime("2023-12-19 12:00:00")] = np.nan
decadal_df.loc[pd.to_datetime("2023-12-21 12:00:00")] = np.nan
'''

#decadal_df = decadal_df.dropna(axis = 0, how = 'all')
print(decadal_df)

path = "Pictures/Data-Hovmoller/"
isExist = os.path.exists(path)
if not isExist:
    # Create a new directory because it does not exist
    os.makedirs(path)
decadal_df.to_csv(path +  str(FAA) + "-" + str(config.start_year) + "-radiosonde.csv")



opposing_wind_probability = decadal_df.to_numpy()

opposing_wind_probability = opposing_wind_probability.astype(float)
#print(opposing_wind_probability)


#Create timestamps for plotting, that match dataset
#base = dt.datetime(2012, 1, 1)
#dates = decadal_df.index #[base + dt.timedelta(x,'M') for x in range(0, 144)]
#monthsx, altsx = np.meshgrid(dates,decadal_df.columns)
#opposing_wind_probability = opposing_wind_probability.T

#print(decadal_df.index)
#print(decadal_df.columns)
#print(opposing_wind_probability.T)

from matplotlib.colors import LinearSegmentedColormap, rgb_to_hsv, hsv_to_rgb


def shifted_hsv_colormap():
    """
    Create a shifted HSV colormap with red in the middle and cyan on the outsides.
    """
    hsv = plt.cm.hsv(np.linspace(0, 1, 256))  # Original HSV colormap
    # Shift the colormap
    shift_amount = 0.35  # 0.5 corresponds to shifting 180 degrees (red in the center)
    shifted_hsv = np.roll(hsv, int(shift_amount * len(hsv)), axis=0)
    return LinearSegmentedColormap.from_list('shifted_hsv', shifted_hsv)


def brighten_and_saturate_colormap(cmap, brightness_factor=1.5, saturation_factor=1.5):
    """
    Adjust both brightness and saturation of a colormap in HSV space.

    Parameters:
    - cmap: The original colormap to adjust.
    - brightness_factor: A multiplier for the brightness (default is 1.5).
    - saturation_factor: A multiplier for the saturation (default is 1.5).

    Returns:
    - A new colormap with enhanced brightness and saturation.
    """
    colors = cmap(np.linspace(0, 1, 256))  # Sample the colormap
    # Convert RGB to HSV
    hsv_colors = rgb_to_hsv(colors[:, :3])  # Ignore alpha channel
    # Scale brightness (Value) and saturation
    hsv_colors[:, 1] = np.clip(hsv_colors[:, 1] * saturation_factor, 0, 1)  # Saturation
    hsv_colors[:, 2] = np.clip(hsv_colors[:, 2] * brightness_factor, 0, 1)  # Brightness
    # Convert back to RGB
    adjusted_colors = hsv_to_rgb(hsv_colors)
    # Create a new colormap
    return LinearSegmentedColormap.from_list('bright_saturated_' + cmap.name, adjusted_colors)

# Create a colormap with increased brightness and saturation
bright_saturated_twilight = brighten_and_saturate_colormap(plt.cm.twilight,
                                                           brightness_factor=1.5,
                                                           saturation_factor=1)


# Use the custom colormap
shifted_cmap = shifted_hsv_colormap()


import colorcet as cc


bs_csm = brighten_and_saturate_colormap(cc.cm.CET_C6s,
                                        brightness_factor=1.25,
                                        saturation_factor=1.25)

#6s is best, 8s, then 7s


#Plotting
fig, ax = plt.subplots(1, 1 , figsize=(18,3))
#im = ax.pcolormesh(decadal_df.index, decadal_df.columns, opposing_wind_probability.T, vmin=0, vmax=360, cmap='rainbow')
im = ax.contourf(decadal_df.index, decadal_df.columns, opposing_wind_probability.T, levels=np.linspace(0, 360., 19), cmap=bs_csm)

if lat >= 0:
    plt.title(Station_Name + "- " + CO + " (Station #" + str(WMO).zfill(5) + ") - " + str(int(lat)) + "$^\circ$N",
              fontsize=12)
else:
    plt.title(Station_Name + "- " + CO + " (Station #" + str(WMO).zfill(5) + ") - " + str(int(-1 * lat)) + "$^\circ$N",
              fontsize=12)


#plt.title("Puntas Arenas, Chile (53$^\circ$S)" +
#          "\nWind Directionality for Station #" + str(WMO).zfill(5) +  " in " + str(config.start_year), fontsize=13)

plt.title(Station_Name + "- " + CO +
          "\nWind Directionality for Station #" + str(WMO).zfill(5) +  " in " + str(config.start_year), fontsize=13)
plt.ylabel('Altitude (m)')
plt.xlabel('Date')

divider = make_axes_locatable(plt.gca())
cax = divider.append_axes("right", "1%", pad="1%")
im.set_clim(0.,360.)
cbar = fig.colorbar(im, cax=cax, boundaries=np.linspace(0, 360, 13))

cbar.set_label("Wind Direction (degrees)", labelpad=10)

ax.xaxis.set_minor_locator(YearLocator(1))
ax.xaxis.set_minor_formatter(DateFormatter('%Y'))
for tick in ax.xaxis.get_minor_ticks():
    tick.tick1line.set_markersize(0)
    tick.tick2line.set_markersize(0)
    tick.label1.set_horizontalalignment('center')

for tick in ax.yaxis.get_major_ticks()[::2]:
    tick.set_visible(False)


fig.tight_layout()
plt.tight_layout()
plt.margins(0.1)
#plt.bbox_inches='tight'

path = "Pictures/Hovmoller-Full-Winds/"
isExist = os.path.exists(path)
if not isExist:
    # Create a new directory because it does not exist
    os.makedirs(path)
plt.savefig("Pictures/Hovmoller/" +  str(FAA), bbox_inches='tight')
print("Saving...")
#plt.savefig(path +  str(FAA) + "-" + str(config.start_year) + "-NO-TITLE", bbox_inches='tight')
plt.show()
