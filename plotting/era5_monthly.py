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
import os

year = config.start_year

continent = "North_America"
stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv", index_col=1)
#stations_df = stations_df.loc[stations_df["CO"] == "US"]

#'''
continent2 = "South_America"
stations_df2 = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent2 + ".csv", index_col=1)

stations_df = pd.concat([stations_df, stations_df2])
stations_df = stations_df[~stations_df.index.duplicated(keep='first')]
#'''


stations_df = utils.convert_stations_coords(stations_df)

print(stations_df)

#Generate a new dataframe of montly probaibilties for each station to add to the stations_df. Take the max probability (per alt/pres)
month_columns = list(range(1, 13))
era5_frames = []
radiosonde_frames = []

stations_df_radiosonde = stations_df.copy()
stations_df_era5 = stations_df.copy()
stations_df_error = stations_df.copy()
#asda



for row in stations_df.itertuples(index = 'WMO'):
    WMO = row.Index
    FAA = row.FAA
    Name = row.Station_Name

    radiosonde_analysis = config.parent_dir + 'radiosonde_ANALYSIS_' + config.type + '/'
    era5_analysis = config.parent_dir + 'era5_ANALYSIS_' + config.type + '/'

    analysis_folder = config.analysis_folder

    #file_name = analysis_folder[:-14]  + "analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'
    radiosonde_path = radiosonde_analysis + str(FAA) + " - " + str(WMO) + "/analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'
    era5_path = era5_analysis + str(FAA) + " - " + str(WMO) + "/analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'

    missing_paths = [path for path in (radiosonde_path, era5_path) if not os.path.exists(path)]
    if missing_paths:
        print("Skipping " + str(FAA) + " - " + str(WMO) +
              ": missing " + ", ".join(missing_paths))
        continue

    radiosonde = utils.subset_probability_columns(
        pd.read_csv(radiosonde_path, index_col=0)
    )
    era5 = utils.subset_probability_columns(
        pd.read_csv(era5_path, index_col=0)
    )

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

    era5_frames.append(df)

    #--------------------------------------

    df = radiosonde  # radiosonde/(difference+.01)

    avg = np.nanmean(df.max())

    df = df.T
    df = df.apply(['max'])
    # df.index.max = 'WMO'
    df = df.rename(index={'max': WMO})
    df.index.set_names('WMO', level=None, inplace=True)

    radiosonde_frames.append(df)

if not radiosonde_frames or not era5_frames:
    raise RuntimeError(
        "No paired radiosonde/ERA5 " + config.type
        + " analysis files were found for " + str(year)
    )

df_radiosonde = pd.concat(radiosonde_frames, ignore_index=False).reindex(columns=month_columns)
df_era5 = pd.concat(era5_frames, ignore_index=False).reindex(columns=month_columns)
df_error = df_radiosonde - df_era5
stations_df = stations_df.loc[df_radiosonde.index]
print(df_error)
print(colored(df_era5,"yellow"))
print(colored(df_radiosonde, "cyan"))




stations_df_radiosonde = pd.concat([stations_df_radiosonde, df_radiosonde], axis=1)
stations_df_era5 = pd.concat([stations_df_era5, df_era5], axis=1)
stations_df_error =  pd.concat([stations_df_error, df_error], axis=1)

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

#'''
stations_df_error = stations_df_error.apply(pd.to_numeric, errors='coerce')
stations_df_error_lat_means = stations_df_error.copy()
stations_df_error_lat_means.drop(stations_df_error_lat_means.index, inplace=True)



for i in range (0,19+8):

    lat_range = stations_df_error.loc[stations_df_error['lat_era5'].between(i*5-55, i*5-55+5)] #.mean(numeric_only=True)
    lat_range.loc['mean'] = lat_range.mean()
    print(lat_range)

    stations_df_error_lat_means.loc[i*5-55] = lat_range.loc['mean']



stations_df_radiosonde_lat_means = stations_df_radiosonde_lat_means[[i for i in range(1,13)]]
stations_df_era5_lat_means = stations_df_era5_lat_means[[i for i in range(1,13)]]
stations_df_error_lat_means = stations_df_error_lat_means[[i for i in range(1,13)]]
#'''

#stations_df_radiosonde_lat_means = stations_df_radiosonde_lat_means[[i for i in range(1,13)]]
#stations_df_era5_lat_means = stations_df_era5_lat_means[[i for i in range(1,13)]]

stations_df_radiosonde_lat_means['mean'] = stations_df_radiosonde_lat_means.mean(axis=1)
stations_df_era5_lat_means['mean'] = stations_df_era5_lat_means.mean(axis=1)
stations_df_error_lat_means['mean'] = stations_df_error_lat_means.mean(axis=1)


#Drop latitude region 5, becaue of so few stations?
#stations_df_radiosonde_lat_means = stations_df_radiosonde_lat_means.drop([stations_df_radiosonde_lat_means.index[12]])
#stations_df_era5_lat_means = stations_df_era5_lat_means.drop([stations_df_era5_lat_means.index[12]])


print(stations_df_radiosonde_lat_means)
print(stations_df_era5_lat_means)

# ============================================================================

# =======================================
# Plotting
output_folder = os.path.join(
    'Pictures', 'ERA5_vs_Radiosonde_trends', str(year), config.type
)
os.makedirs(output_folder, exist_ok=True)
level_label = "Altitude-based" if config.type == "ALT" else "Pressure-level-based"
output_prefix = "era5-vs-radiosonde-" + config.type.lower() + "-" + str(year)
# =======================================
# Plotting
# Plot individual monthly latitude comparison plots and save them
for month in range(1, 13):
    plt.figure(figsize=(10, 6))
    plt.plot(stations_df_radiosonde_lat_means[month], stations_df_radiosonde_lat_means.index, color="blue", label="Radiosonde")
    plt.plot(stations_df_era5_lat_means[month], stations_df_era5_lat_means.index, color="red", label="ERA5")
    plt.plot(stations_df_error_lat_means[month], stations_df_error_lat_means.index, color="black", label="ERROR")
    plt.title(f"{level_label} Opposing Wind Probabilities by Latitude, Month {month}")
    plt.ylabel("Latitude")
    plt.xlabel("Opposing Wind Probability")
    plt.legend()
    plt.tight_layout()

    # Save the figure with month number as file name
    plt.savefig(os.path.join(output_folder, output_prefix + f"-month-{month}.png"))
    plt.close()  # Close the figure to avoid display and memory issues

# Annual latitude comparison plot and save it
plt.figure(figsize=(12, 6))
plt.plot(stations_df_radiosonde_lat_means.index, stations_df_radiosonde_lat_means["mean"], color="blue", label="Radiosondes")
plt.plot(stations_df_era5_lat_means.index, stations_df_era5_lat_means["mean"], color="red", label="ERA5")
plt.title(f"Annual Mean Opposing Wind Probabilities by Latitude in {year}")
plt.xlabel("Latitude")
plt.ylabel("Annual Mean Opposing Wind Probability")
plt.legend()
plt.tight_layout()

# Save the annual plot with month number as file name
plt.savefig(os.path.join(output_folder, output_prefix + "-annual-latitude-means.png"))
plt.close()

# 3D plot of latitudes with monthly data and save it
fig = plt.figure(figsize=(12, 12))
ax = fig.add_subplot(projection='3d')

colors = cm.hsv(np.linspace(0, 1, 13))
for i in range(1, 13):
    ax.scatter(stations_df.lat_era5, df_radiosonde[i], df_era5[i], color=colors[i], alpha=.6)

ax.plot(stations_df_radiosonde_lat_means.index, stations_df_radiosonde_lat_means["mean"], stations_df_era5_lat_means["mean"], color="black", markersize=7, linewidth=3, marker="o", label="MEAN")

ax.set_xlabel("Latitude")
ax.set_ylabel("Radiosonde Opposing Winds Probabilities")
ax.set_zlabel("ERA5 Reanalysis Forecast Opposing Winds Probabilities")
ax.set_title(f"{level_label} Opposing Wind Probabilities by Latitude in {year}")

ax.legend()

# Save the 3D plot with month number as file name
plt.savefig(os.path.join(output_folder, output_prefix + "-latitude-3d.png"))
plt.close()
