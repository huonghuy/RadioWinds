"""
This script compares overall opposing wind differences between radiosondes and a corresponding era5 forecast.

This assumes batchAnalysis.py (for OW's) has been run twice for North and South America, once for radiosondes by pressure,and once for era5 by pressure

It outputs 3 plots. 2d error scatter plot, 3D error scatter plot,  and an average probabilities plot by 5 degrees latitude.
"""


import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
import numpy as np
from termcolor import colored
import sys
sys.path.insert(0, sys.path[0] + '/../') #add config from 1 directory up.

import config
import utils
import pickle

year = config.start_year

continent = "North_America"
stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv", index_col=1)
#stations_df = stations_df.loc[stations_df["CO"] == "US"]

#'''
continent2 = "South_America"
stations_df2 = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent2 + ".csv", index_col=1)

stations_df = pd.concat([stations_df, stations_df2])
#'''


stations_df = utils.convert_stations_coords(stations_df)

print(stations_df)

#Generate a new dataframe of montly probaibilties for each station to add to the stations_df. Take the max probability (per alt/pres)
df_error = pd.DataFrame(columns=[i for i in range(1,12)])

df_era5 = pd.DataFrame(columns=[i for i in range(1,12)])
df_radiosonde = pd.DataFrame(columns=[i for i in range(1,12)])

print(df_radiosonde)

stations_df_radiosonde = stations_df.copy()
stations_df_era5 = stations_df.copy()
#asda



for row in stations_df.itertuples(index = 'WMO'):
    WMO = row.Index
    FAA = row.FAA
    Name = row.Station_Name

    radiosonde_analysis = config.parent_dir  + 'radiosonde' + '_ANALYSIS_' + 'ALT' + '/'
    era5_analysis = config.parent_dir + 'era5' + '_ANALYSIS_' + 'ALT-new' + '/'

    analysis_folder = config.analysis_folder

    #file_name = analysis_folder[:-14]  + "analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'
    radiosonde = radiosonde_analysis + str(FAA) + " - " + str(WMO) + "/analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'
    era5 = era5_analysis + str(FAA) + " - " + str(WMO) + "/analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'


    radiosonde = pd.read_csv(radiosonde, index_col=0 )
    era5 = pd.read_csv(era5, index_col=0 )

    print(FAA, Name)
    #print(radiosonde)
    #print(era5)

    #------------------------------

    df = era5  # radiosonde/(difference+.01)

    avg = np.nanmean(df.max())

    df = df.T
    df = df.apply(['max'])
    # df.index.max = 'WMO'
    df = df.rename(index={'max': WMO})
    df.index.set_names('WMO', level=None, inplace=True)

    df_era5 = pd.concat([df_era5, df], ignore_index=False)

    #--------------------------------------

    df = radiosonde  # radiosonde/(difference+.01)

    avg = np.nanmean(df.max())

    df = df.T
    df = df.apply(['max'])
    # df.index.max = 'WMO'
    df = df.rename(index={'max': WMO})
    df.index.set_names('WMO', level=None, inplace=True)

    df_radiosonde = pd.concat([df_radiosonde, df], ignore_index=False)

    df_error = df_radiosonde-df_era5


print(df_error)
print(colored(df_era5,"yellow"))
print(colored(df_radiosonde, "cyan"))




stations_df_radiosonde = pd.concat([stations_df_radiosonde, df_radiosonde], axis=1)
stations_df_era5 = pd.concat([stations_df_era5, df_era5], axis=1)

print(stations_df_radiosonde)


#for averaging....



'''
bins =  np.arange(-55, 60, 5)

#df['bins_a_mean'] = stations_df_radiosonde.groupby('bins_a')['a'].transform('mean')

groups = stations_df_radiosonde.groupby(pd.cut(stations_df_radiosonde.lat_era5, bins))
print("ok)")
print(groups)
groups
print(groups.mean())
#ind = np.digitize(df['B'], bins)

print(bins)
'''


stations_df_radiosonde = stations_df_radiosonde.apply(pd.to_numeric, errors='coerce')
stations_df_radiosonde_lat_means = stations_df_radiosonde.copy()
stations_df_radiosonde_lat_means.drop(stations_df_radiosonde_lat_means.index, inplace=True)

for i in range (0,19+8):

    lat_range = stations_df_radiosonde.loc[stations_df_radiosonde['lat_era5'].between(i*5-55, i*5-55+5)] #.mean(numeric_only=True)
    lat_range.loc['mean'] = lat_range.mean()
    print(lat_range)

    stations_df_radiosonde_lat_means.loc[i*5-55] = lat_range.loc['mean']








stations_df_era5 = stations_df_era5.apply(pd.to_numeric, errors='coerce')
stations_df_era5_lat_means = stations_df_era5.copy()
stations_df_era5_lat_means.drop(stations_df_era5_lat_means.index, inplace=True)

for i in range (0,19+8):

    lat_range = stations_df_era5.loc[stations_df_era5['lat_era5'].between(i*5-55, i*5-55+5)] #.mean(numeric_only=True)
    lat_range.loc['mean'] = lat_range.mean()
    print(lat_range)

    stations_df_era5_lat_means.loc[i*5-55] = lat_range.loc['mean']



stations_df_radiosonde_lat_means = stations_df_radiosonde_lat_means[[i for i in range(1,13)]]
stations_df_era5_lat_means = stations_df_era5_lat_means[[i for i in range(1,13)]]

stations_df_radiosonde_lat_means['mean'] = stations_df_radiosonde_lat_means.mean(axis=1)
stations_df_era5_lat_means['mean'] = stations_df_era5_lat_means.mean(axis=1)


#Drop latitude region 5, becaue of so few stations?
#stations_df_radiosonde_lat_means = stations_df_radiosonde_lat_means.drop([stations_df_radiosonde_lat_means.index[12]])
#stations_df_era5_lat_means = stations_df_era5_lat_means.drop([stations_df_era5_lat_means.index[12]])


print(stations_df_radiosonde_lat_means)
print(stations_df_era5_lat_means)

# ============================================================================

# PLOTTTING

'''
ax2 = stations_df.plot.scatter(x=df_radiosonde[1],
                      y=df_radiosonde[2],
                      c=3,
                      colormap='viridis')
'''
Months = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']

colors = cm.hsv(np.linspace(0, 1, 13))

for i in range(1,13):
    plt.scatter(df_radiosonde[i], df_era5[i], color = colors[i], label=Months[i])

#Bias line
# Add a diagonal line (x = y) for comparison
min_value = min(np.min(df_radiosonde[1:].values), np.min(df_era5[1:].values))  # min of both datasets
max_value = max(np.max(df_radiosonde[1:].values), np.max(df_era5[1:].values))  # max of both datasets

print(min_value,max_value)
# Create a diagonal line between the min and max values of the data
plt.plot([0, 1], [0, 1], color='black', linestyle='-')



plt.legend()

plt.xlabel("Radiosonde opposing wind probability")
plt.ylabel("ERA5 Reanalysis Forecast opposing wind probability")
plt.title("Comparison of Pressure level based Opposing Wind Probabilities between Radiosondes \n"
          "and ERA5 Reanalysis Forecasts in "  + str(year) + " in North America")


fig = plt.figure(figsize=(12, 12))
ax = fig.add_subplot(projection='3d')

#df.shape[0]
month = np.empty(df_radiosonde.shape[0])
month.fill(1)

for i in range(1,13):
    ax.scatter(stations_df.lat_era5, df_radiosonde[i], df_era5[i], color = colors[i], alpha = .6)

'''
for i in range(1,13):
    ax.plot(stations_df_radiosonde_lat_means.index, stations_df_radiosonde_lat_means[i], stations_df_era5_lat_means[i], color = colors[i], marker = "o")
'''

ax.plot(stations_df_radiosonde_lat_means.index, stations_df_radiosonde_lat_means["mean"], stations_df_era5_lat_means["mean"], color = "black", markersize = 7, linewidth= 3, marker = "o", label="MEAN")

ax.set_xlabel("Latitude")
ax.set_ylabel("Radiosonde Opposing Winds Probabilities")
ax.set_zlabel("ERA5 Reanalysis Forecast Opposing Winds Probabilities")
ax.set_title("Comparison of Pressure level based Opposing Wind Probabilities between Radiosondes \n"
          "and ERA5 Reanalysis Forecasts and Latitude in " + str(year) + " in the Western Hemisphere")

ax.legend(Months[1:])

fig2 = plt.figure(figsize=(12, 6))
plt.plot(stations_df_radiosonde_lat_means.index, stations_df_radiosonde_lat_means["mean"], color = "blue", markersize = 7, linewidth= 3, marker = "o", label="radiosondes")
plt.plot(stations_df_radiosonde_lat_means.index, stations_df_era5_lat_means["mean"], color = "red", markersize = 7, linewidth= 3, marker = "o", label="era5")
plt.tight_layout()
plt.legend()
plt.title("Annual Mean Opposing Wind Probabilities by Latitude \n"
          "in the Western Hemisphere in " + str(year))
plt.ylabel("Annual Mean Opposing Wind Probability")
plt.xlabel("Latitude")

#pickle.dump(fig, open('ERA5-Radiosonde-Lat-3DSCATTER-2023.fig.pickle', 'wb')) # This is for Python 3 - py2 may need `file` instead of `open`

plt.show()