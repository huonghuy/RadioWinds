"""
Generates Figures 1 and A1 in the manuscript"""

from os import listdir
import pandas as pd
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator,  DateFormatter
import os



import sys
sys.path.append(os.path.dirname(os.path.abspath('/mnt/d/RadioWinds/config.py')))

import config
import utils

FAA = config.plot_station
WMO = utils.lookupWMO(FAA)
Station_Name = utils.lookupStationName(FAA)
CO = utils.lookupCountry(FAA)
lat,lon,el = utils.lookupCoordinate(FAA)
print(WMO, FAA, Station_Name, lat,lon,el)

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

                directions = utils.binned_wind_directions(df, labels, config.alt_step)

                date_chunks = file[:-4].split('-')
                time = pd.Timestamp(*map(int, date_chunks[1:5]))
                wind_directions.loc[time, :] = directions

                #print(wind_directions)

                #asfa

                #wind_directions = wind_directions.sort_values(by=wind_directions.index)

    return(wind_directions)


decadal_df = getDecadalMonthlyMeans(FAA, WMO)
print(decadal_df)


decadal_df = decadal_df.sort_index()

decadal_df.index = pd.to_datetime(decadal_df.index)

# Preserve every missing 00/12 UTC launch as a blank cell.
decadal_df = utils.regularize_sounding_grid(decadal_df, config.start_year, config.end_year)
missing_days = decadal_df.isna().all(axis=1).groupby(
    decadal_df.index.normalize()
).all().sum()
print(f"Entirely missing days left blank: {missing_days}")

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
decadal_df.to_csv(path + str(FAA) + "-" + config.plot_year_range_token + "-radiosonde.csv")



opposing_wind_probability = np.ma.masked_invalid(
    decadal_df.to_numpy(dtype=float).T
)
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
plot_cmap = bs_csm.copy()
plot_cmap.set_bad('white')
ax.set_facecolor('white')
im = ax.pcolormesh(
    decadal_df.index,
    decadal_df.columns,
    opposing_wind_probability,
    vmin=0,
    vmax=360,
    cmap=plot_cmap,
    shading='nearest',
)

hemisphere = "N" if lat >= 0 else "S"
period = config.plot_year_range_label
plt.title(
    f"{Station_Name} - {CO} (Station #{str(WMO).zfill(5)}) - {abs(int(lat))}°{hemisphere}"
    f"\nWind Directionality, {period}",
    fontsize=13,
)
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
plt.savefig(path + str(FAA) + "-" + config.plot_year_range_token, bbox_inches='tight')
print("Saving...")
#plt.savefig(path +  str(FAA) + "-" + str(config.start_year) + "-NO-TITLE", bbox_inches='tight')
plt.show()
