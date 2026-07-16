'''
This script produces decadal mean and standard deviation maps for opposing winds

Soundings data needs to already be downloaded (AnnualWyomingDownload.py) and analyzed (batchAnalysis.py).
So does decadal mean and std analysis (decadal_ow_analysis.py)

Many parameters can be modified in the configuration parameters below.
'''


import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import cartopy.feature as cfeature
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
import sys
sys.path.insert(0, sys.path[0] + '/../') #add config from 1 directory up.
import os
import config
import utils

#GRID DATA EXAMPLES
# https://scitools.org.uk/cartopy/docs/v0.13/matplotlib/advanced_plotting.html
# https://climate-cms.org/posts/2020-09-22-wrapping-pcolormesh.html
# https://pbett.wordpress.com/datafun/plotting-maps/
# https://xarray.pydata.org/en/v0.7.0/plotting.html


#MAP CONFIGURATION:
#--------------------------------------
font = {'size'   : 22}
plt.rc('font', **font)

method = 'nearest'
year = config.start_year
res = 1 # degrees
lons = np.arange(min_lon,max_lon,res)
lats = np.arange(min_lat,max_lat,res)
grid_x, grid_y = np.meshgrid(lons, lats)

#--------------------------
# Load every station once (coordinates are region/type independent).
base_stations = utils.getWorldStations()
#continent = "North_America"
#stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv", index_col=1)

#continent2 = "South_America"
#stations_df2 = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent2 + ".csv", index_col=1)

#base_stations = pd.concat([stations_df, stations_df2])

base_stations = utils.convert_stations_coords(base_stations)
# Several regional station lists overlap; keep one row per WMO so interpolation
# is not biased by duplicate entries in the combined world catalog.
base_stations = base_stations.loc[~base_stations.index.duplicated(keep='first')].copy()

path = config.maps_folder
os.makedirs(path, exist_ok=True)
range_label = utils.probability_range_label()


def load_probabilities(type):
    """WMO-indexed dataframe of each station's monthly decadal `type` (mean/std)."""
    df_probabilities = pd.DataFrame(columns=[i for i in range(1, 13)])
    for row in base_stations.itertuples(index='WMO'):
        WMO = row.Index
        FAA = row.FAA
        file_name = (config.analysis_folder + str(FAA) + " - " + str(WMO)
                     + '/analysis-wind_probabilities-DECADAL-STATISTICS.csv')
        if not os.path.exists(file_name):
            print(f"skipping {FAA} - {WMO}: missing decadal statistics for {range_label}")
            continue
        df = pd.read_csv(file_name, index_col=0).T
        if type not in df.index:
            print(f"skipping {FAA} - {WMO}: missing {type} row in {file_name}")
            continue
        df = df.drop('std' if type == 'mean' else 'mean')
        df = df.rename(index={type: WMO})
        df.index.set_names('WMO', level=None, inplace=True)
        df_probabilities = pd.concat([df_probabilities, df], ignore_index=False)
    return df_probabilities


def wrap_longitudes_180(lons):
    """Convert longitude array to the [-180, 180) convention."""
    return ((np.asarray(lons, dtype=float) + 180.0) % 360.0) - 180.0


def lonlat_to_unit_xyz(lons_deg, lats_deg):
    """Project lon/lat coordinates to a unit sphere for KD-tree queries."""
    lons_rad = np.deg2rad(wrap_longitudes_180(lons_deg))
    lats_rad = np.deg2rad(np.asarray(lats_deg, dtype=float))
    cos_lat = np.cos(lats_rad)
    return np.column_stack((
        cos_lat * np.cos(lons_rad),
        cos_lat * np.sin(lons_rad),
        np.sin(lats_rad),
    ))


def chord_to_km(chord):
    """Convert unit-sphere chord distance to great-circle distance in km."""
    clipped = np.clip(np.asarray(chord, dtype=float) / 2.0, 0.0, 1.0)
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(clipped)


def build_coverage_mask(grid_lons, grid_lats, station_lons, station_lats):
    """
    Keep only grid cells that lie within a reasonable distance of their nearest
    valid station. The local cutoff is derived from each station's nearest
    neighboring station to avoid continent-scale bleed in sparse regions.
    """
    if len(station_lons) == 0:
        return np.zeros(grid_lons.shape, dtype=bool)

    station_xyz = lonlat_to_unit_xyz(station_lons, station_lats)
    tree = cKDTree(station_xyz)

    if len(station_lons) == 1:
        station_radius_km = np.array([MAX_COVERAGE_KM])
    else:
        station_chord, _ = tree.query(station_xyz, k=2)
        nearest_station_km = chord_to_km(station_chord[:, 1])
        station_radius_km = np.clip(
            nearest_station_km * COVERAGE_FACTOR,
            MIN_COVERAGE_KM,
            MAX_COVERAGE_KM,
        )

    grid_xyz = lonlat_to_unit_xyz(grid_lons.ravel(), grid_lats.ravel())
    grid_chord, station_idx = tree.query(grid_xyz, k=1)
    grid_nearest_km = chord_to_km(grid_chord)

    allowed_km = station_radius_km[np.asarray(station_idx, dtype=int)]
    return (grid_nearest_km <= allowed_km).reshape(grid_lons.shape)


# Make every (type x region x month) map.
for type, tcfg in TYPES.items():
    # Attach this quantity's monthly probabilities to a fresh station frame so the
    # two types don't contaminate each other.
    stations_df = base_stations.join(load_probabilities(type))
    # Drop stations that collected no data for any month.
    month_cols = list(range(1, 12 + 1))
    stations_df = stations_df.dropna(subset=month_cols, how='all')

    for region, rcfg in REGIONS.items():
        lons = np.arange(rcfg['min_lon'], rcfg['max_lon'], res)
        lats = np.arange(rcfg['min_lat'], rcfg['max_lat'], res)
        grid_x, grid_y = np.meshgrid(lons, lats)

        for month in range(1, 12 + 1):
            values = stations_df.loc[:, month].to_numpy()
            lonlat = stations_df[['lon_era5', 'lat_era5']].copy()
            valid = (
                np.isfinite(values)
                & np.isfinite(lonlat['lon_era5'].to_numpy())
                & np.isfinite(lonlat['lat_era5'].to_numpy())
            )
            if valid.sum() < 2:
                print(f"skipping {region} {type} month {month}: not enough valid stations")
                continue

            values = values[valid]
            lonlat = lonlat.loc[valid].copy()
            # The grid (lons) is in 0-360 convention, but convert_stations_coords
            # returns -180..180. Wrap the points into 0-360 so the nearest-neighbor
            # interpolation matches the grid; otherwise stations on the wrong side
            # of the dateline numerically hijack grid cells.
            lonlat['lon_era5'] = lonlat['lon_era5'] % 360
            points = lonlat.to_numpy()

            zi = griddata(points, values, (grid_x, grid_y), method=method)
            if USE_COVERAGE_MASK:
                coverage_mask = build_coverage_mask(
                    grid_x,
                    grid_y,
                    lonlat['lon_era5'].to_numpy(),
                    lonlat['lat_era5'].to_numpy(),
                )
                zi = np.where(coverage_mask, zi, np.nan)

            fig = plt.figure(figsize=(12, 12))
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(rcfg['extent'])

            D = ax.pcolormesh(lons, lats, zi, transform=ccrs.PlateCarree(),
                              cmap=tcfg['cmap'], alpha=.9,
                              vmin=tcfg['vmin'], vmax=tcfg['vmax'])
            cbar_kw = {'extend': tcfg['extend']} if tcfg['extend'] else {}
            fig.colorbar(D, ax=ax, shrink=.5, pad=.01, **cbar_kw)

            ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=2)
            ax.add_feature(cfeature.STATES.with_scale('50m'))

            # Plot Radiosonde Locations
            ax.scatter(stations_df['lon_era5'], stations_df['lat_era5'], marker=".",
                       c="blue", s=55, transform=ccrs.Geodetic(), zorder=200)
            ax.scatter(stations_df['lon_era5'], stations_df['lat_era5'], marker=".",
                       c="cyan", s=4, transform=ccrs.Geodetic(), zorder=200)

            ax.add_feature(cfeature.OCEAN, facecolor='gray', alpha=1, zorder=150)

            ax.set_title(Months[month] + "\n" + range_label, fontsize=30)
            fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

            print("generating " + region + " " + type + " map for month " + str(month))

            fname = "DECADAL-" + region + "-" + type.upper() + "-" + str(month)
            plt.savefig(path + "/" + fname, bbox_inches='tight')
            plt.close(fig)
