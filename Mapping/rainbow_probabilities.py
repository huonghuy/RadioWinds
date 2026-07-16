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
prefix = "World-Opposing"  #title of the maps that are exported to the MAPS folder

#These are the values download from Copernicus for 2022 in degrees
'''
#Western Hemisphere
min_lat = -65
max_lat = 75
min_lon = 360-175
max_lon = 360-20
'''
'''
#CONUS
min_lat = -65
max_lat = 75
min_lon = 360-175
max_lon = 360-20
'''

# World
min_lat = -90
max_lat = 90
min_lon = 0
max_lon = 360

res = 1 # degrees

lons = np.arange(min_lon,max_lon,res)
lats = np.arange(min_lat,max_lat,res)

grid_x, grid_y = np.meshgrid(lons, lats)

#--------------------------
#continent = "North_America"
#stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv", index_col=1)

# Uncomment this if South America has been downloaded and Analyzed as well
#'''
#continent2 = "South_America"
#stations_df2 = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent2 + ".csv", index_col=1)

stations_df = utils.getWorldStations() #pd.concat([stations_df, stations_df2])
#'''

#Generate a new dataframe of montly probaibilties for each station to add to the stations_df. Take the max probability (per alt/pres)
df_probabilities = pd.DataFrame(columns=[i for i in range(1,12)])

for row in stations_df.itertuples(index = 'WMO'):
    WMO = row.Index
    FAA = row.FAA
    Name = row.Station_Name

    analysis_folder = config.analysis_folder

    #file_name = analysis_folder[:-14]  + "analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'
    #file_name = analysis_folder + str(FAA) + " - " + str(WMO) + "/analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'
    #file_name = analysis_folder + str(FAA) + " - " + str(WMO) + "/analysis_" + str(year) + '-wind_probabilities-CALM.csv'
    file_name = analysis_folder + str(FAA) + " - " + str(WMO) + "/analysis_" + str(year) + '-wind_probabilities-TOTAL.csv'

    df = pd.read_csv(file_name, index_col=0 )


    # Opposing Winds
    #'''
    df = df.T
    df = df.apply(['max'])
    df = df.rename(index={'max': WMO})
    df.index.set_names('WMO', level=None, inplace=True)
    #'''

    # Calm Winds
    '''
    #Not sure how to get rid of this future warning, So going to leave as is for now
    #if not df.isnull().values.all(): #to handle deprecation warning
    df["alt"] = pd.to_numeric(df.idxmax(axis=1))
    df[df['alt'] < 15] = -99. # remove altitudes under
    df = df.T
    df = df.query("index == 'alt'")
    df = df.rename(index={'alt': WMO})
    df.index.set_names('WMO', level=None, inplace=True)
    '''


    df_probabilities = pd.concat([df_probabilities, df], ignore_index=False)

stations_df = stations_df.join(df_probabilities)
print(stations_df)


#Convert Ranges of Coordinates from stations list for Cartopy
#stations_df[' LONG'] = stations_df.apply(lambda x: (360-x[' LONG'] if x['E'] == 'W' else 1*x[' LONG']), axis = 1)
#stations_df['  LAT'] = stations_df.apply(lambda x: (-1*x['  LAT'] if x['N'] == 'S' else 1*x['  LAT']), axis = 1)

#Convert Station Coordinates for mapping
stations_df = utils.convert_stations_coords(stations_df)


#Drop any stations that collected no data for the entire year.
stations_df.dropna(subset=df.columns[-12:], how = 'all', inplace = True)



# Make a new plot for each month
for month in range (1,12+1):
    #stations_df.dropna(subset=[month], inplace = True)
    values = stations_df.loc[:,month].to_numpy()
    lonlat = stations_df[['lon_era5','lat_era5']]
    points = lonlat.to_numpy()

    zi = griddata(points,values,(grid_x, grid_y),method=method)


    # North America
    #extent = [-125 , -70, 20, 50]

    # Western Hemisphere
    #extent = [-170, -20, -25, 40]

    # World
    extent = [-180, 180, -90, 90]


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
