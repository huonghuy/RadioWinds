"""
This script generates a decadal hovmoller plot of opposing wind probabilities by date and altitude for an individual station.
"""

import config
from os import listdir
import os
import pandas as pd
import numpy as np
import datetime as dt
import utils
from mpl_toolkits.axes_grid1 import make_axes_locatable

import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, YearLocator, WeekdayLocator, DateFormatter
import matplotlib.ticker as ticker

FAA = "SCCI"
WMO = utils.lookupWMO(FAA)
Station_Name = utils.lookupStationName(FAA)
CO = utils.lookupCountry(FAA)
lat,lon,el = utils.lookupCoordinate(FAA)
print(WMO, FAA, Station_Name, lat,lon,el)

def getDecadalMonthlyMeans(FAA, WMO):
    decadal_df = None
    #for year in range (config.start_year, config.end_year +1):
    analysis_folder = utils.get_analysis_folder(FAA, WMO, config.start_year)
    analysis_folder = os.path.dirname(os.path.dirname(analysis_folder)) + "/" #Go up one level to get annual
    #analysis_folder = analysis_folder[:-13]  #go up one directory

    files = [f for f in listdir(analysis_folder) if f.endswith(".csv")]
    print(analysis_folder)
    print(files)

    #Iterate through for one year vs decadal
    if config.start_year != config.end_year:
        for file in files:
            print(file)
            try:
                # Extract year from the file name
                year = int(file[9:-29])  # Adjust indices based on your file naming pattern
                print(f"Processing file: {file}, Year: {year}")

                df = pd.read_csv(analysis_folder + file, index_col=0)
                df.index = pd.to_datetime(dict(year=year, month=df.index, day=1))

                if decadal_df is None:
                    decadal_df = df.copy()
                else:
                    decadal_df = pd.concat([decadal_df, df])

            except:
                pass #skip for decadal analysis files.
    else:
        for file in files:
            try:
                # Extract year from the file name
                year = int(file[9:-29])  # Adjust indices based on your file naming pattern
                print(f"Processing file: {file}, Year: {year}")

                # Only process files matching the target year
                if year == config.start_year:
                    df = pd.read_csv(analysis_folder + file, index_col=0)
                    df.index = pd.to_datetime(dict(year=year, month=df.index, day=1))

                    # Concatenate data into the decadal_df
                    if decadal_df is None:
                        decadal_df = df.copy()
                    else:
                        decadal_df = pd.concat([decadal_df, df])
                else:
                    print(f"Skipping file: {file} (Year: {year} does not match target year {config.start_year})")

            except Exception as e:
                print(f"Error processing file {file}: {e}")
                pass  # Skip files that don't conform to the expected pattern or have issues

    return (decadal_df)


decadal_df = getDecadalMonthlyMeans(FAA, WMO)

opposing_wind_probability = decadal_df.to_numpy()
#Create timestamps for plotting, that match dataset
#base = dt.datetime(2012, 1, 1)
dates = decadal_df.index #[base + dt.timedelta(x,'M') for x in range(0, 144)]
monthsx, altsx = np.meshgrid(dates,decadal_df.columns)
opposing_wind_probability = opposing_wind_probability.T

#Plotting
fig, ax = plt.subplots(1, 1 , figsize=(18,3))
#im = ax.pcolormesh(decadal_df.index, decadal_df.columns, opposing_wind_probability, cmap='RdYlGn', vmin=0, vmax=1)
im = ax.contourf(decadal_df.index, decadal_df.columns, opposing_wind_probability, levels=np.linspace(0, 1., 11), cmap='RdYlGn', vmin=0., vmax=1.)

if lat >= 0:
    plt.title(Station_Name + "- " + CO + " (Station #" + str(WMO).zfill(5) + ") - " + str(int(lat)) + "$^\circ$N",
              fontsize=12)
else:
    plt.title(Station_Name + "- " + CO + " (Station #" + str(WMO).zfill(5) + ") - " + str(int(-1 * lat)) + "$^\circ$N",
              fontsize=12)

plt.ylabel('Altitude (km)')
plt.xlabel('Date')


divider = make_axes_locatable(plt.gca())
cax = divider.append_axes("right", "1%", pad="1%")
im.set_clim(0.,1.)
cbar = fig.colorbar(im, cax=cax, boundaries=np.linspace(0, 1, 11))

cbar.set_label("Opposing Winds Probability", labelpad=10)

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

folder_path = "Pictures/Hovmoller-OW/" # + str(FAA) + "/"
if not os.path.exists(folder_path):
        os.makedirs(folder_path)

if config.start_year == config.end_year:
    plt.savefig(folder_path + str(config.mode) + "-optimized-WH-" + str(config.type) + "-" + str(FAA)+ "-" + str(config.start_year),
                bbox_inches='tight')
else:
    plt.savefig(folder_path + str(config.mode) + "-optimized-WH-" + str(config.type) + "-" + str(FAA)+ "-DECADAL",
                bbox_inches='tight')
plt.show()