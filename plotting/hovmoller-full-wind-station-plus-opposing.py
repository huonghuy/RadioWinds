from os import listdir
import os
import pandas as pd
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.pyplot as plt
import colorcet as cc
from matplotlib.dates import YearLocator,  DateFormatter

import config
import utils

FAA = config.plot_station
WMO = utils.lookupWMO(FAA)
Station_Name = utils.lookupStationName(FAA)
CO = utils.lookupCountry(FAA)
lat, lon, el = utils.lookupCoordinate(FAA)
print(WMO, FAA, Station_Name, lat, lon, el)


labels = np.arange(config.min_alt, config.max_alt, config.alt_step)
wind_directions = pd.DataFrame(columns=labels)


def getDecadalMonthlyMeans(FAA, WMO):
    decadal_df = None
    for year in range (config.start_year, config.end_year +1):
        for month in range (1,13):
            suffix = str(month) + "/"


            analysis_folder = utils.get_data_folder(FAA, WMO, year) +suffix
            files = [f for f in listdir(analysis_folder) if f.endswith(".csv")]
            print(files)
            for file in files:

                df = pd.read_csv(analysis_folder + file, index_col=0)

                if config.type == "ALT":
                    df.dropna(subset=['height'], how='all', inplace=True)
                    df = df.drop(df[df['height'] < config.min_alt].index)
                    df = df.drop(df[df['height'] > config.max_alt].index)





                directions = utils.binned_wind_directions(df, labels, config.alt_step)

                print(directions)


                date_chunks = file[:-4].split('-')
                time = pd.Timestamp(*map(int, date_chunks[1:5]))

                wind_directions.loc[time, :] = directions

                print(wind_directions)

                #asfa

                #wind_directions = wind_directions.sort_values(by=wind_directions.index)

    return(wind_directions)


decadal_df = getDecadalMonthlyMeans(FAA, WMO)


decadal_df = decadal_df.sort_index()

decadal_df.index = pd.to_datetime(decadal_df.index)
# Preserve every missing 00/12 UTC launch as a blank cell.
decadal_df = utils.regularize_sounding_grid(decadal_df, config.start_year, config.end_year)
#decadal_df = (decadal_df.reindex(pd.date_range('2023-01-01', '2023-12-31', freq='D'))
#      .fillna(np.nan))


#decadal_df.loc[decadal_df.index,datetime("2023-02-05 00:00:00")]=np.nan
#decadal_df.loc[decadal_df.index,datetime("2023-03-05 00:00:00")]=np.nan

#SBBV 2023
'''
decadal_df.loc[pd.to_datetime("2023-02-05 00:00:00")] = np.nan
decadal_df.loc[pd.to_datetime("2023-03-04 00:00:00")] = np.nan
decadal_df.loc[pd.to_datetime("2023-06-26 00:00:00")] = np.nan
decadal_df.loc[pd.to_datetime("2023-08-08 00:00:00")] = np.nan
'''
decadal_df = decadal_df.sort_index()

#decadal_df = decadal_df.dropna(axis = 0, how = 'all')
print(decadal_df)


opposing_wind_probability = np.ma.masked_invalid(decadal_df.to_numpy(dtype=float).T)
print(opposing_wind_probability)


#Create timestamps for plotting, that match dataset
#base = dt.datetime(2012, 1, 1)
#dates = decadal_df.index #[base + dt.timedelta(x,'M') for x in range(0, 144)]
#monthsx, altsx = np.meshgrid(dates,decadal_df.columns)
#opposing_wind_probability = opposing_wind_probability.T

print(decadal_df.index)
print(decadal_df.columns)
print(opposing_wind_probability)

#Plotting
fig, ax = plt.subplots(1, 1 , figsize=(18,3))
#im = ax.pcolormesh(decadal_df.index, decadal_df.columns, opposing_wind_probability, cmap='RdYlGn', vmin=0, vmax=1)
#im = ax.pcolormesh(decadal_df.index, decadal_df.columns, opposing_wind_probability.T, vmin=0, vmax=360, cmap='rainbow')
plot_cmap = cc.cm.CET_C6s.copy()
plot_cmap.set_bad("white")
ax.set_facecolor("white")
im = ax.pcolormesh(
    decadal_df.index, decadal_df.columns, opposing_wind_probability,
    vmin=0, vmax=360, cmap=plot_cmap, shading="nearest",
)

#plt.title("Fairbanks, Alaska USA (65$^\circ$N)" +
#plt.title("Pittsburgh, Pennsylvania USA (40$^\circ$N)" +
#plt.title("Hilo, Hawaii USA (15$^\circ$N)" +
#plt.title("Wind Directionality for Station " + FAA +  " in " + str(config.start_year), fontsize=13)
hemisphere = "N" if lat >= 0 else "S"
period = config.plot_year_range_label
plt.title(
    f"{Station_Name} - {CO} (Station #{str(WMO).zfill(5)}) - {abs(int(lat))}°{hemisphere}"
    f"\nWind Directionality, {period}",
    fontsize=13,
)
plt.ylabel('Altitude (m)')
plt.xlabel('Date')
#fig.colorbar(im)


divider = make_axes_locatable(plt.gca())
cax = divider.append_axes("right", "1%", pad="1%")
#plt.colorbar(im, cax=cax)
#im.set_array(opposing_wind_probability)
im.set_clim(0.,360.)
cbar = fig.colorbar(im, cax=cax, boundaries=np.linspace(0, 360, 13))

cbar.set_label("Wind Direction (degrees)", labelpad=10)

#cbar.ax.set_ylabel('Wind Direction (degrees)', rotation=270)

'''
# make labels centered
ax.xaxis.set_major_locator(MonthLocator())
ax.xaxis.set_minor_locator(MonthLocator(bymonth=12))

ax.xaxis.set_major_formatter(ticker.NullFormatter())
ax.xaxis.set_minor_formatter(DateFormatter('%b'))

'''

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
path = "Pictures/Hovmoller-Full-Winds-Plus_Opposing/"
os.makedirs(path, exist_ok=True)
plt.savefig(path + str(FAA) + "-" + config.plot_year_range_token, bbox_inches='tight')
plt.show()
