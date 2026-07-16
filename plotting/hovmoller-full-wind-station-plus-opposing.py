from os import listdir
import pandas as pd
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator,  DateFormatter

import config
import utils

FAA = "ABQ"
WMO = utils.lookupWMO(FAA)
Station_Name = utils.lookupStationName(FAA)
print(WMO, FAA, Station_Name)


wind_bins = np.arange(config.min_alt-500, config.max_alt, config.alt_step)
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





                df['wind_bin'] = pd.cut(df['height'], wind_bins+501, labels = labels)

                print(df)

                #df = pd.to_numeric(df, errors='coerce')
                directions = df.groupby('wind_bin')['direction'].mean()
                directions = directions.interpolate(method='nearest')

                print(directions)


                date_chunks = file[:-4].split('-')
                time = datetime(config.start_year, int(date_chunks[2]), int(date_chunks[3]), int(date_chunks[4]), 0, 0)

                wind_directions.loc[time, :] = directions

                print(wind_directions)

                #asfa

                #wind_directions = wind_directions.sort_values(by=wind_directions.index)

    return(wind_directions)


decadal_df = getDecadalMonthlyMeans(FAA, WMO)


decadal_df = decadal_df.sort_index()

decadal_df.index = pd.to_datetime(decadal_df.index)
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


opposing_wind_probability = decadal_df.to_numpy()

opposing_wind_probability = opposing_wind_probability.astype(float)
print(opposing_wind_probability)


#Create timestamps for plotting, that match dataset
#base = dt.datetime(2012, 1, 1)
#dates = decadal_df.index #[base + dt.timedelta(x,'M') for x in range(0, 144)]
#monthsx, altsx = np.meshgrid(dates,decadal_df.columns)
#opposing_wind_probability = opposing_wind_probability.T

print(decadal_df.index)
print(decadal_df.columns)
print(opposing_wind_probability.T)

#Plotting
fig, ax = plt.subplots(1, 1 , figsize=(18,3))
#im = ax.pcolormesh(decadal_df.index, decadal_df.columns, opposing_wind_probability, cmap='RdYlGn', vmin=0, vmax=1)
#im = ax.pcolormesh(decadal_df.index, decadal_df.columns, opposing_wind_probability.T, vmin=0, vmax=360, cmap='rainbow')
im = ax.contourf(decadal_df.index, decadal_df.columns, opposing_wind_probability.T, levels=np.linspace(0, 360., 13), cmap='rainbow')

#plt.title("Fairbanks, Alaska USA (65$^\circ$N)" +
#plt.title("Pittsburgh, Pennsylvania USA (40$^\circ$N)" +
#plt.title("Hilo, Hawaii USA (15$^\circ$N)" +
#plt.title("Wind Directionality for Station " + FAA +  " in " + str(config.start_year), fontsize=13)
plt.title("Perth, Australia (32$^\circ$S)" +
          "\nWind Directionality for Station " + FAA +  " in " + str(config.start_year), fontsize=13)
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
plt.savefig("Pictures/Hovmoller/" +  str(FAA), bbox_inches='tight')
plt.savefig("Pictures/Hovmoller-Full-Winds-Plus_Opposing/" +  str(FAA) + "-" + str(config.start_year), bbox_inches='tight')
plt.show()