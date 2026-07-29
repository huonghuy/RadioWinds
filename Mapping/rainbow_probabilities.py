import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import cartopy.feature as cfeature
from scipy.interpolate import griddata
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
prefix = "Western-Hemisphere"  #title of the maps that are exported to the MAPS folder

#These are the values download from Copernicus for 2022 in degrees

#Western Hemisphere
min_lat = -65
max_lat = 75
min_lon = 360-175
max_lon = 360-20

'''
#CONUS
min_lat = -65
max_lat = 75
min_lon = 360-175
max_lon = 360-20
'''

'''
# World
min_lat = -90
max_lat = 90
min_lon = 0
max_lon = 360
'''

res = 1 # degrees

lons = np.arange(min_lon,max_lon,res)
lats = np.arange(min_lat,max_lat,res)

grid_x, grid_y = np.meshgrid(lons, lats)

#--------------------------
'''
continent = "North_America"
stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv", index_col=1)

# Uncomment this if South America has been downloaded and Analyzed as well

continent2 = "South_America"
stations_df2 = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent2 + ".csv", index_col=1)
'''
stations_df = utils.getWorldStations()#stations_df = pd.concat([stations_df, stations_df2])
#'''

# Generate monthly maximum probabilities for each available station.
stations_df = stations_df.loc[~stations_df.index.duplicated(keep="first")].copy()
month_columns = list(range(1, 13))
probability_rows = []
missing_files = 0
empty_files = 0

for row in stations_df.itertuples(index='WMO'):
    WMO = row.Index
    FAA = row.FAA
    file_name = os.path.join(
        config.analysis_folder,
        f"{FAA} - {WMO}",
        f"analysis_{year}-wind_probabilities-TOTAL.csv",
    )
    if not os.path.exists(file_name):
        missing_files += 1
        continue

    annual = pd.read_csv(file_name, index_col=0).apply(
        pd.to_numeric, errors="coerce"
    )
    annual.index = pd.to_numeric(annual.index, errors="coerce")
    annual = annual.loc[annual.index.notna()]
    annual.index = annual.index.astype(int)

    monthly_max = annual.max(axis=1, skipna=True).reindex(month_columns)
    if monthly_max.isna().all():
        empty_files += 1
        continue
    monthly_max.name = WMO
    probability_rows.append(monthly_max)

if not probability_rows:
    raise RuntimeError(
        f"No populated annual probability files found for {year}; "
        f"{missing_files} were missing and {empty_files} were empty."
    )

df_probabilities = pd.DataFrame(probability_rows).reindex(columns=month_columns)
df_probabilities.index.name = "WMO"
print(
    f"Loaded {len(df_probabilities)} station files; skipped "
    f"{missing_files} missing and {empty_files} empty files."
)

stations_df = stations_df.join(df_probabilities)
print(stations_df)


#Convert Ranges of Coordinates from stations list for Cartopy
#stations_df[' LONG'] = stations_df.apply(lambda x: (360-x[' LONG'] if x['E'] == 'W' else 1*x[' LONG']), axis = 1)
#stations_df['  LAT'] = stations_df.apply(lambda x: (-1*x['  LAT'] if x['N'] == 'S' else 1*x['  LAT']), axis = 1)

# Keep geographic coordinates in -180..180 for Cartopy. A separate 0..360
# longitude is created below only for interpolation against the 0..360 grid.
stations_df = utils.convert_stations_coords(stations_df)


#Drop any stations that collected no data for the entire year.
stations_df.dropna(subset=month_columns, how='all', inplace=True)



# Make a new plot for each month
for month in range (1,12+1):
    #stations_df.dropna(subset=[month], inplace = True)
    values = pd.to_numeric(stations_df.loc[:, month], errors="coerce").to_numpy()
    lonlat = stations_df[['lon_era5', 'lat_era5']].copy()
    valid = (
        np.isfinite(values)
        & np.isfinite(lonlat['lon_era5'].to_numpy())
        & np.isfinite(lonlat['lat_era5'].to_numpy())
    )
    if valid.sum() < 2:
        print("Skipping month " + str(month) + ": not enough valid stations")
        continue

    values = values[valid]
    lonlat = lonlat.loc[valid].copy()
    # The interpolation grid uses 0..360 longitudes, while
    # convert_stations_coords returns -180..180. Wrap only the interpolation
    # copy so its coordinates match the grid; keep the original geographic
    # longitudes for plotting station markers below.
    lonlat['lon_era5'] = lonlat['lon_era5'] % 360
    points = lonlat.to_numpy()

    # A full-world grid has a numeric seam at 0/360 even though those
    # meridians are adjacent geographically. Cyclic copies prevent stations
    # near one side from being invisible to interpolation on the other side.
    # Regional grids do not need or receive these extra points.
    if max_lon - min_lon >= 360 - res:
        points_west = points.copy()
        points_west[:, 0] -= 360
        points_east = points.copy()
        points_east[:, 0] += 360
        points = np.vstack([points_west, points, points_east])
        values = np.tile(values, 3)

    zi = griddata(points,values,(grid_x, grid_y),method=method)


    # North America
    #extent = [-125 , -70, 20, 50]

    # Western Hemisphere
    extent = [-170, -20, -25, 40]

    # World
    #extent = [-180, 180, -90, 90]


    central_lon = np.mean(extent[:2])
    central_lat = np.mean(extent[2:])

    fig = plt.figure(figsize=(12, 12))

    # ax = plt.axes(projection=ccrs.AlbersEqualArea(central_lon, central_lat))
    # ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=stn_lon))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent(extent)

    # Calm Winds Altitude Levels:
    '''
    #cmap = plt.cm.get_cmap('rainbow')
    #cmap = matplotlib.colormaps['rainbow']
    cmap = plt.colormaps['rainbow']
    cmap.set_under('black')
    cmap.set_bad('white', 1.)
    D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(), cmap=cmap, alpha=.8, vmin=15, vmax=28, shading='auto')
    '''

    '''
    # Calm Winds Probabilities:
    D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(), cmap='RdYlGn', alpha=.8, vmin=0, vmax=1., shading='auto')
    fig.colorbar(D, ax=ax, shrink=.5, pad=.01)
    '''

    # Opposing Winds:
    #'''
    D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(), cmap='RdYlGn', alpha=.8, vmin=0, vmax=1., shading='auto')
    fig.colorbar(D, ax=ax, shrink=.5, pad=.01)
    #'''

    # Full Winds:
    '''
    D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(), cmap='RdYlGn', alpha=.8, vmin=1, vmax=16.,
                      shading='auto')
    fig.colorbar(D, ax=ax, shrink=.5, pad=.01)
    '''


    ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=2)
    ax.add_feature(cfeature.STATES.with_scale('50m'))

    # Plot Radiosonde Locations
    ax.scatter(stations_df['lon_era5'], stations_df['lat_era5'], marker = ".", c = "blue", s= 55, transform = ccrs.Geodetic(), zorder=200)
    ax.scatter(stations_df['lon_era5'], stations_df['lat_era5'], marker = ".", c = "cyan", s= 4, transform = ccrs.Geodetic(), zorder=200)

    ax.add_feature(cfeature.OCEAN, facecolor = 'gray', alpha = 1, zorder = 150)

    #ax.set_title(prefix + " " + config.mode + "_" + config.type+ "_" + "\n Opposing Winds Probabilities\n Alt:{15-25 km} in " + calendar.month_name[month] + " " + str(year), fontsize=24)
    ax.set_title(str(month) + "-" + str(year))
    plt.tight_layout()

    print("generating map for " + prefix + "_" + config.type+ "_" + config.mode +  "-" + str(year) + '-' + str(month))

    path = config.maps_folder + str(year) + "/"
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)

    #Weird windows bug where this doesn't overwrite teh saved fig date, but the file changes?
    #plt.savefig(path + prefix + "_" + config.type+ "_" + config.mode + "-" + str(year) + '-' + str(month)+ "-CALM")
    plt.savefig(path + prefix + "_" + config.type + "_" + config.mode + "-" + str(year) + '-' + str(month), bbox_inches='tight')
    plt.close()
    #plt.show()
