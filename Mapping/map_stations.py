import cartopy.crs as ccrs
import cartopy.io
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
#import iris
import glob
import os
import sys
sys.path.insert(0, sys.path[0] + '/../') #add config from 1 directory up.
import utils
import config


#import xarray as xr

'''
fname = cartopy.io.shapereader.natural_earth(resolution='10m',
                                               category='cultural',
                                               name='populated_places_simple')
'''

#https://www.weather.gov/gjt/education_corner_balloon

#fname = iris.sample_data_path('rotated_pole.nc')
#temperature = iris.load_cube(fname)
#
#print(temperature)
#
#temperature.coord('grid_latitude').guess_bounds()
#temperature.coord('grid_longitude').guess_bounds()
#
#gridlons = temperature.coord('grid_longitude').contiguous_bounds()
#gridlats = temperature.coord('grid_latitude').contiguous_bounds()
#temperature = temperature.data


path = 'Radiosonde_Stations_Info/CLEANED/'
all_files = glob.glob(os.path.join(path, "*.csv"))

stations_df = pd.concat((pd.read_csv(f) for f in all_files), ignore_index=True)


#continent = "North_America"
#stations_df = pd.read_csv('Radisonde_Stations_Info/CLEANED/' + continent + ".csv")

print(stations_df)
#print(stations_df.columns)

#ds=xr.open_dataset(fname)
#print(ds)

'''
plt.figure(figsize=(12, 6))
ax = plt.axes(projection=ccrs.Robinson())

ax.set_title('Populated places of the world.')
ax.coastlines()

points = list(cartopy.io.shapereader.Reader(fname).geometries())
'''

#central_lat = 37.5
#central_lon = -96
#extent = [-180, -20, 0, 45]
#central_lon = np.mean(extent[:2])
#central_lat = np.mean(extent[2:])

central_lat = 0
central_lon = 0
extent = [-180, 180, -90, 90]
central_lon = np.mean(extent[:2])
central_lat = np.mean(extent[2:])

#plt.figure()
plt.figure(figsize=(15, 8))
#ax = plt.axes(projection=ccrs.AlbersEqualArea(central_lon, central_lat))
ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=central_lon))
ax.set_extent(extent)

ax.add_feature(cartopy.feature.OCEAN)
#ax.add_feature(cartopy.feature.STATES, edgecolor='black', linewidth=0.5)
ax.add_feature(cartopy.feature.BORDERS, edgecolor='black', linewidth=0.5)
ax.add_feature(cartopy.feature.LAND, color = 'white', edgecolor='black')
#ax.add_feature(cartopy.feature.LAKES, edgecolor='black')
#ax.add_feature(cartopy.feature.RIVERS)
ax.gridlines()

#Convert Station Coordinates for mapping
stations_df = utils.convert_stations_coords(stations_df)

stations_df_used =  stations_df[stations_df.Continent.isin(['North_America',"South_America"])]
stations_df_notused =  stations_df[~stations_df.Continent.isin(['North_America',"South_America"])]

ax.scatter(stations_df_notused['lon_era5'], stations_df_notused['lat_era5'], c = "blue", s= 8, transform = ccrs.Geodetic())
ax.scatter(stations_df_used['lon_era5'], stations_df_used['lat_era5'], c = "red", s= 8, transform = ccrs.Geodetic())

#rotated_pole = ccrs.RotatedPole(pole_longitude=177.5, pole_latitude=37.5)

path = config.maps_folder + str(config.end_year) + "/"
isExist = os.path.exists(path)
if not isExist:
    # Create a new directory because it does not exist
    os.makedirs(path)

#plt.title("Launch Sites in University of Wyoming Global Radiosonde Archive")
plt.tight_layout()
plt.savefig(path + 'UofWy-Radiosonde-World_map', bbox_inches='tight')

plt.show()