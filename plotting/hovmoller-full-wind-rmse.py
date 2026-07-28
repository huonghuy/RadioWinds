import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.dates import YearLocator, DateFormatter
import utils
import os
import config

FAA = config.plot_station
WMO = utils.lookupWMO(FAA)
Station_Name = utils.lookupStationName(FAA)
CO = utils.lookupCountry(FAA)
lat,lon,el = utils.lookupCoordinate(FAA)
print(WMO, FAA, Station_Name, lat,lon,el)


path = "Pictures/Data-Hovmoller/"
# Load the CSV files
era5_file = path + FAA + "-" + str(config.start_year) + "-era5.csv"
radiosonde_file = path + FAA + "-" + config.plot_year_range_token + "-radiosonde.csv"

era5_df = pd.read_csv(era5_file)
radiosonde_df = pd.read_csv(radiosonde_file)

# Convert time columns to datetime format
era5_df.rename(columns={'Unnamed: 0': 'time'}, inplace=True)
radiosonde_df.rename(columns={'Unnamed: 0': 'time'}, inplace=True)

era5_df['time'] = pd.to_datetime(era5_df['time'])
radiosonde_df['time'] = pd.to_datetime(radiosonde_df['time'])

# Set time as index for easier alignment
era5_df.set_index('time', inplace=True)
radiosonde_df.set_index('time', inplace=True)

# Convert column names (altitudes) to floats
era5_df.columns = era5_df.columns.astype(float)
radiosonde_df.columns = radiosonde_df.columns.astype(float)

#SBBV 2023
#radiosonde_df.loc[pd.to_datetime("2023-02-04 12:00:00")] = np.nan
#radiosonde_df.loc[pd.to_datetime("2023-06-26 12:00:00")] = np.nan

#SCSN
'''
radiosonde_df.loc[pd.to_datetime("2023-04-03 12:00:00")] = np.nan
radiosonde_df.loc[pd.to_datetime("2023-04-07 12:00:00")] = np.nan
radiosonde_df.loc[pd.to_datetime("2023-09-28 12:00:00")] = np.nan
radiosonde_df.loc[pd.to_datetime("2023-09-30 12:00:00")] = np.nan
radiosonde_df.loc[pd.to_datetime("2023-12-19 12:00:00")] = np.nan
radiosonde_df.loc[pd.to_datetime("2023-12-21 12:00:00")] = np.nan
'''


# Step 1: Regrid ERA5 data to match radiosonde altitude levels
era5_regridded = pd.DataFrame(index=era5_df.index, columns=radiosonde_df.columns)



for timestamp in era5_df.index:
    era5_regridded.loc[timestamp] = utils.interpolate_directions(
        era5_df.columns, era5_df.loc[timestamp].to_numpy(), radiosonde_df.columns
    )

#Ensure both DataFrames have exactly the same time index
era5_regridded = era5_regridded.reindex(radiosonde_df.index)

print(era5_regridded)
print(radiosonde_df)

angular_difference = np.abs(era5_regridded - radiosonde_df)
angular_difference = angular_difference.where(
    angular_difference <= 180, 360 - angular_difference
)


print(angular_difference)
#dfgdfg


fig, ax = plt.subplots(1, 1 , figsize=(18,3))
opposing_wind_probability = np.ma.masked_invalid(
    angular_difference.to_numpy(dtype=float).T
)

plt.title(
    f"{Station_Name} - {CO}\nERA5 vs Radiosonde Angular Difference, {config.start_year}",
    fontsize=12,
)



plot_cmap = plt.cm.magma.copy()
plot_cmap.set_bad("white")
ax.set_facecolor("white")
im = ax.pcolormesh(
    angular_difference.index, angular_difference.columns, opposing_wind_probability,
    vmin=0, vmax=180, cmap=plot_cmap, shading="nearest",
)

#plt.title("Salt Lake City Utah (40$^\circ$N)" +
#          "\nWind Directionality for Station #" + str(WMO).zfill(5) +  " in " + str(config.start_year), fontsize=13)

#plt.title(Station_Name + "- " + CO +
#          "\nWind Directionality for Station #" + str(WMO).zfill(5) +  " in " + str(config.start_year), fontsize=13)
plt.ylabel('Altitude (m)')
plt.xlabel('Date')



divider = make_axes_locatable(plt.gca())
cax = divider.append_axes("right", "1%", pad="1%")
im.set_clim(0.,180.)
cbar = fig.colorbar(im, cax=cax, boundaries=np.linspace(0, 180, 13))

cbar.set_label("Angular Difference (degrees)", labelpad=10)



ax.xaxis.set_minor_locator(YearLocator(1))
ax.xaxis.set_minor_formatter(DateFormatter('%Y'))
for tick in ax.xaxis.get_minor_ticks():
    tick.tick1line.set_markersize(0)
    tick.tick2line.set_markersize(0)
    tick.label1.set_horizontalalignment('center')

for tick in ax.yaxis.get_major_ticks()[::2]:
    tick.set_visible(False)




fig.tight_layout()

path = "Pictures/Hovmoller-DIFF/"
isExist = os.path.exists(path)
if not isExist:
    # Create a new directory because it does not exist
    os.makedirs(path)
#plt.savefig("Pictures/Hovmoller/" +  str(FAA), bbox_inches='tight')
plt.savefig(
    path + str(FAA) + "-radiosonde-" + config.plot_year_range_token
    + "-era5-" + str(config.start_year),
    bbox_inches='tight',
)
fig.tight_layout()
plt.show()
#dfgdfg






