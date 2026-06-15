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



continent = "North_America"
stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv", index_col=1)
#stations_df = stations_df.loc[stations_df["CO"] == "US"]


continent2 = "South_America"
stations_df2 = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent2 + ".csv", index_col=1)

stations_df = pd.concat([stations_df, stations_df2])



#Generate a new dataframe of montly probaibilties for each station to add to the stations_df. Take the max probability (per alt/pres)
df_probabilities = pd.DataFrame(columns=[i for i in range(1,12)])

for row in stations_df.itertuples(index = 'WMO'):
    WMO = row.Index
    FAA = row.FAA
    Name = row.Station_Name

    radiosonde_analysis = config.analysis_folder
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

    difference = (radiosonde - era5) #.abs()
    #print(difference)
    df = difference # radiosonde/(difference+.01)
    #df = df/df.max()

    avg  = np.nanmean(df.max())
    print()
    print(df)
    print("avg:", avg)
    print()

    #asfa

    #sdfs

    df = df.T
    df = df.apply(['max'])
    #df.index.max = 'WMO'
    df = df.rename(index={'max': WMO})
    df.index.set_names('WMO', level=None, inplace=True)

    df_probabilities = pd.concat([df_probabilities, df], ignore_index=False)

stations_df = stations_df.join(df_probabilities)
print(stations_df)



#Convert Ranges of Coordinates from stations list for Cartopy
stations_df[' LONG'] = stations_df.apply(lambda x: (360-x[' LONG'] if x['E'] == 'W' else 1*x[' LONG']), axis = 1)
stations_df['  LAT'] = stations_df.apply(lambda x: (-1*x['  LAT'] if x['N'] == 'S' else 1*x['  LAT']), axis = 1)


#Drop any stations that collected no data for the entire year.
stations_df.dropna(subset=df.columns[-12:], how = 'all', inplace = True)



# Make a new plot for each month
for month in range (1,12+1):
    #stations_df.dropna(subset=[month], inplace = True)
    values = stations_df.loc[:,month].to_numpy()
    lonlat = stations_df[[' LONG','  LAT']]
    points = lonlat.to_numpy()

    values = stations_df.loc[:,month].to_numpy()
    lonlat = stations_df[[' LONG','  LAT']]
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



    extent = [-160, -32, -33, 50] # Western Hemisphere
    #extent = [min_lon-10, max_lon + 10, min_lat-10, max_lat +10]
    #extent = [(min_lon -360)-20, (max_lon -360)-15, min_lat - 1, max_lat]



    central_lon = np.mean(extent[:2])
    central_lat = np.mean(extent[2:])

    fig = plt.figure(figsize=(12, 12))
    #ax = plt.axes(projection=ccrs.AlbersEqualArea(central_lon, central_lat))
    ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=stn_lon))
    ax.set_extent(extent)


    #ax = plt.axes(projection=ccrs.PlateCarree())
    #D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(), cmap='gist_heat_r', alpha=.8, vmin=0, vmax=1)
    D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(), cmap='seismic', alpha=.8, vmin=-1, vmax=1)
    #Remove individual color bars for appendix figure
    #cbar = fig.colorbar(D, ax=ax, shrink=.5, pad=.01)
    #cbar.ax.yaxis.set_major_formatter(PercentFormatter(1, 0))
    #fig.colorbar.set_ylim(0, 1)
    #plt.clim(0,1)
    #ax.scatter(stn_lon, stn_lat, transform=ccrs.PlateCarree(), marker='+', s=100, c='k', linewidth=3)
    ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=2)
    ax.add_feature(cfeature.STATES.with_scale('50m'))

    # Plot Radiosonde Locations
    ax.scatter(stations_df[' LONG'], stations_df['  LAT'], marker = ".", c = "blue", s= 55, transform = ccrs.Geodetic(), zorder=200)
    ax.scatter(stations_df[' LONG'], stations_df['  LAT'], marker = ".", c = "cyan", s= 4, transform = ccrs.Geodetic(), zorder=200)

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

    print("generating map for " + prefix + "_" + config.type+ "_" + config.mode +  "-" + str(year) + '-' + str(month))

    path = config.maps_folder + "/" + str(year)
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)

    plt.savefig(path +"/" +  prefix + "_" + config.type+ "_" + config.mode + "-" + str(year) + '-' + str(month) +".jpg", bbox_inches='tight')
    #plt.show()
