import cartopy.crs as ccrs
import cartopy.io
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import pandas as pd
import numpy as np
import cartopy.feature as cfeature
from scipy.interpolate import griddata
import calendar
import sys
sys.path.insert(0, sys.path[0] + '/../') #add config from 1 directory up.
import os
import config
import utils

#Example stuff ---------------------
#GRID DATA EXAMPLES
# https://scitools.org.uk/cartopy/docs/v0.13/matplotlib/advanced_plotting.html
# https://climate-cms.org/posts/2020-09-22-wrapping-pcolormesh.html
# https://pbett.wordpress.com/datafun/plotting-maps/
# https://xarray.pydata.org/en/v0.7.0/plotting.html


#--------------------------------------
#DOWNLOAD THE DATA

#MAP CONFIGURATION STUFF:
method = 'nearest'
year = config.start_year
prefix = "DIFF_Western_Hemisphere"  #title of the maps that are exported to the MAPS folder
comparison_label = "radiosonde-minus-era5"

# Difference-map settings apply to the paired radiosonde/ERA5 product. They
# must not depend on config.mode, because both datasets are always required.
map_extent = [-160, -30, -60, 75]
difference_min = -1
difference_max = 1


#These are the values download from Copernicus for 2022 in degrees
min_lat = 0
max_lat = 75
min_lon = 360-160
max_lon = 360-50
res = 1 # degrees


min_lat = -75
max_lat = 75
min_lon = 360-160
max_lon = 360-30
res = 1 # degrees

lons = np.arange(min_lon,max_lon,res)
lats = np.arange(min_lat,max_lat,res)

grid_x, grid_y = np.meshgrid(lons, lats)



#--------------------------


def load_annual_probabilities(analysis_root, station_directory, year):
    annual_filename = "analysis_" + str(year) + "-wind_probabilities-TOTAL.csv"
    annual_path = os.path.join(
        analysis_root,
        station_directory,
        annual_filename,
    )

    if os.path.exists(annual_path):
        annual = pd.read_csv(annual_path, index_col=0).apply(
            pd.to_numeric, errors="coerce"
        )
        if not annual.empty:
            return annual

    monthly_directory = os.path.join(analysis_root, station_directory, str(year) + "_analysis")
    monthly_rows = []
    monthly_prefix = station_directory + "-" + str(year) + "-"
    for month in range(1, 13):
        monthly_path = os.path.join(
            monthly_directory,
            monthly_prefix + str(month) + ".csv",
        )
        if not os.path.exists(monthly_path):
            continue

        monthly = pd.read_csv(monthly_path, index_col=0).apply(
            pd.to_numeric, errors="coerce"
        )
        if "average" not in monthly.index:
            print("Skipping " + monthly_path + ": no average row")
            continue

        mean_row = monthly.loc["average"]
        mean_row.name = month
        monthly_rows.append(mean_row)

    if monthly_rows:
        print("Using monthly files for " + station_directory + ": annual file is missing or empty")
        return pd.DataFrame(monthly_rows)

    return pd.DataFrame()



continent = "North_America"
stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv", index_col=1)


continent2 = "South_America"
stations_df2 = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent2 + ".csv", index_col=1)

stations_df = pd.concat([stations_df, stations_df2])



#Generate a new dataframe of montly probaibilties for each station to add to the stations_df. Take the max probability (per alt/pres)
df_probabilities = pd.DataFrame(
    index=pd.Index([], name="WMO"),
    columns=range(1, 13),
    dtype=float,
)

for row in stations_df.itertuples(index = 'WMO'):
    WMO = row.Index
    FAA = row.FAA
    Name = row.Station_Name

    station_directory = str(FAA) + " - " + str(WMO)
    radiosonde_root = os.path.join(
        config.parent_dir,
        "radiosonde_ANALYSIS_" + config.type,
    )
    era5_root = os.path.join(
        config.parent_dir,
        "era5_ANALYSIS_" + config.type,
    )

    radiosonde = load_annual_probabilities(radiosonde_root, station_directory, year)
    era5 = load_annual_probabilities(era5_root, station_directory, year)
    radiosonde, era5 = radiosonde.align(era5, join="inner")

    if radiosonde.empty or era5.empty:
        print("Skipping " + station_directory + ": annual radiosonde or ERA5 file is empty")
        continue

    print(FAA, Name)
    #print(radiosonde)
    #print(era5)

    difference = radiosonde - era5
    if not np.isfinite(difference.to_numpy(dtype=float)).any():
        print("Skipping " + station_directory + ": no overlapping numeric values")
        continue
    #print(difference)
    df = difference # radiosonde/(difference+.01)
    #df = df/df.max()

    avg = difference.max(axis=0, skipna=True).mean(skipna=True)
    print()
    print(df)
    print("avg:", avg)
    print()

    #asfa

    #sdfs

    monthly_max = difference.max(axis=1, skipna=True)
    monthly_max.index = pd.to_numeric(monthly_max.index, errors="coerce")
    monthly_max = monthly_max[monthly_max.index.notna()]
    monthly_max.index = monthly_max.index.astype(int)
    valid_months = monthly_max.index.intersection(df_probabilities.columns)
    df_probabilities.loc[WMO, valid_months] = monthly_max.loc[valid_months]

stations_df = stations_df.join(df_probabilities)
print(stations_df)



# Keep geographic coordinates in -180..180 for Cartopy. A separate 0..360
# longitude is created below only for interpolation against the 0..360 grid.
stations_df = utils.convert_stations_coords(stations_df)


#Drop any stations that collected no data for the entire year.
stations_df.dropna(subset=list(range(1, 13)), how='all', inplace=True)



# Make a new plot for each month
for month in range (1,12+1):
    #stations_df.dropna(subset=[month], inplace = True)
    values = pd.to_numeric(stations_df.loc[:, month], errors="coerce").to_numpy()
    lonlat = stations_df[["lon_era5", "lat_era5"]].copy()
    valid = (
        np.isfinite(values)
        & np.isfinite(lonlat["lon_era5"].to_numpy())
        & np.isfinite(lonlat["lat_era5"].to_numpy())
    )
    if valid.sum() < 2:
        print("Skipping month " + str(month) + ": not enough valid stations")
        continue

    values = values[valid]
    lonlat = lonlat.loc[valid]
    lonlat["lon_era5"] = lonlat["lon_era5"] % 360
    points = lonlat.to_numpy()


    #zi = griddata(points,values,(grid_x, grid_y),method='linear', fill_value=0)
    zi = griddata(points,values,(grid_x, grid_y),method=method)

    #print(zi.shape)
    #print(zi)


    #North America
    stn_lat = 40
    stn_lon = -100
    #extent = [-125 , -70, 20, 50]

    #extent = [-165, -60, 0, 75]



    # Show all of North and South America. These are geographic longitude and
    # latitude bounds because set_extent explicitly uses PlateCarree below.
    extent = map_extent
    #extent = [min_lon-10, max_lon + 10, min_lat-10, max_lat +10]
    #extent = [(min_lon -360)-20, (max_lon -360)-15, min_lat - 1, max_lat]



    central_lon = np.mean(extent[:2])
    central_lat = np.mean(extent[2:])

    fig = plt.figure(figsize=(12, 12))
    #ax = plt.axes(projection=ccrs.AlbersEqualArea(central_lon, central_lat))
    ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=stn_lon))
    ax.set_extent(extent, crs=ccrs.PlateCarree())


    #ax = plt.axes(projection=ccrs.PlateCarree())
    #D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(), cmap='gist_heat_r', alpha=.8, vmin=0, vmax=1)
    D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(),
                      cmap='seismic', alpha=.8,
                      vmin=difference_min, vmax=difference_max,
                      shading='auto')
    cbar = fig.colorbar(D, ax=ax, shrink=.6, pad=.01)
    cbar.ax.yaxis.set_major_formatter(PercentFormatter(1, 0))
    #fig.colorbar.set_ylim(0, 1)
    #plt.clim(0,1)
    #ax.scatter(stn_lon, stn_lat, transform=ccrs.PlateCarree(), marker='+', s=100, c='k', linewidth=3)
    ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=2)
    ax.add_feature(cfeature.STATES.with_scale('50m'))

    # Plot Radiosonde Locations
    ax.scatter(stations_df['lon_era5'], stations_df['lat_era5'], marker=".",
               c="blue", s=55, transform=ccrs.Geodetic(), zorder=200)
    ax.scatter(stations_df['lon_era5'], stations_df['lat_era5'], marker=".",
               c="cyan", s=4, transform=ccrs.Geodetic(), zorder=200)

    ax.add_feature(cfeature.OCEAN, facecolor = 'gray', alpha = 1, zorder = 150)

    Months = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
              'November', 'December']
    ax.set_title(Months[month], fontsize=30)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    '''
    ax.set_title(" % Error between Radiosonde and Forecasts \n " +
                 "Opposing Winds Probabilities\n "
                 "Alt:{15-25 km} in " + calendar.month_name[month] + " " + str(year), fontsize=24)
    '''
    plt.tight_layout()

    output_stem = (
        prefix + "_" + config.type + "_" + comparison_label + "-" +
        str(year) + '-' + str(month)
    )
    print("generating map for " + output_stem)

    path = config.maps_folder + "/" + str(year)
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)

    plt.savefig(path + "/" + output_stem + ".jpg", bbox_inches='tight')
    plt.close(fig)
    #plt.show()
