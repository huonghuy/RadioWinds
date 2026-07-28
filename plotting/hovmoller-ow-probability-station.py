"""
This script generates a decadal hovmoller plot of opposing wind probabilities by date and altitude for an individual station.
"""

import config
from os import listdir
import os
import re
import pandas as pd
import numpy as np
import datetime as dt
import utils
from mpl_toolkits.axes_grid1 import make_axes_locatable

import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, YearLocator, WeekdayLocator, DateFormatter
import matplotlib.ticker as ticker

FAA = config.plot_station
WMO = utils.lookupWMO(FAA)
Station_Name = utils.lookupStationName(FAA)
CO = utils.lookupCountry(FAA)
lat,lon,el = utils.lookupCoordinate(FAA)
print(WMO, FAA, Station_Name, lat,lon,el)

def getDecadalMonthlyMeans(FAA, WMO):
    analysis_folder = utils.get_analysis_folder(FAA, WMO, config.start_year)
    analysis_folder = os.path.dirname(os.path.dirname(analysis_folder)) + "/"
    pattern = re.compile(r"^analysis_(\d{4})-wind_probabilities-TOTAL\.csv$")
    frames = []

    for filename in sorted(listdir(analysis_folder)):
        match = pattern.fullmatch(filename)
        if not match:
            continue
        year = int(match.group(1))
        if not config.start_year <= year <= config.end_year:
            continue

        print(f"Processing file: {filename}, Year: {year}")
        frame = pd.read_csv(os.path.join(analysis_folder, filename), index_col=0)
        months = pd.to_numeric(frame.index, errors="raise").astype(int)
        frame.index = pd.to_datetime(dict(year=year, month=months, day=1))
        frames.append(frame)

    if not frames:
        raise FileNotFoundError(
            f"No annual probability CSVs for {config.start_year}–{config.end_year} "
            f"were found in {analysis_folder}"
        )

    result = pd.concat(frames).sort_index()
    full_months = pd.date_range(
        f"{config.start_year}-01-01", f"{config.end_year}-12-01", freq="MS"
    )
    return result.reindex(full_months)


decadal_df = getDecadalMonthlyMeans(FAA, WMO)
decadal_df.columns = pd.to_numeric(decadal_df.columns, errors="raise")

opposing_wind_probability = np.ma.masked_invalid(decadal_df.to_numpy(dtype=float).T)
#Create timestamps for plotting, that match dataset
#base = dt.datetime(2012, 1, 1)
dates = decadal_df.index #[base + dt.timedelta(x,'M') for x in range(0, 144)]
monthsx, altsx = np.meshgrid(dates,decadal_df.columns)

#Plotting
fig, ax = plt.subplots(1, 1 , figsize=(18,3))
#im = ax.pcolormesh(decadal_df.index, decadal_df.columns, opposing_wind_probability, cmap='RdYlGn', vmin=0, vmax=1)
plot_cmap = plt.cm.RdYlGn.copy()
plot_cmap.set_bad("white")
ax.set_facecolor("white")
im = ax.pcolormesh(
    decadal_df.index, decadal_df.columns, opposing_wind_probability,
    vmin=0, vmax=1, cmap=plot_cmap, shading="nearest",
)

hemisphere = "N" if lat >= 0 else "S"
plt.title(
    f"{Station_Name} - {CO} (Station #{str(WMO).zfill(5)}) - {abs(int(lat))}°{hemisphere}\n"
    f"Opposing Wind Probability, {config.plot_year_range_label}",
    fontsize=12,
)

plt.ylabel('Altitude (km)' if config.type == 'ALT' else 'Pressure (hPa)')
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

plt.savefig(
    folder_path + str(config.mode) + "-" + str(config.type) + "-" + str(FAA)
    + "-" + config.plot_year_range_token + ".png",
    bbox_inches='tight',
)
plt.show()
