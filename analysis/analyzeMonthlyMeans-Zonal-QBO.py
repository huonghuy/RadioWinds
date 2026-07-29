'''
This script analyzes monthly zonal wind means from radiosonde data at user specified mandatory pressure levels

pressure can be any of the following  [20, 30, 50, 70, or 100]

NOTE: THIS PROGRAM ASSUMES ALL RADIOSONDES HAVE BEEN DOWNLOADED IN THE
 PROPER ORGANIZATION STRUCTURE USING ANNUALWYOMINGDOWNLOAD.PY.  IF MONTHS ARE MISSING FROM THE DOWNLOAD
 YOU MUST RE-DOWNLOAD FOR THAT STATION OR INCLUDE EMPTY FOLDERS. OTHERWISE THIS PROGRAM WILL NOT COMPLETE.

 Before running you can check if everything is organized correctly with checkRadiosondeDownloads.py

 This script has a significant runtime, especially if many stations are being analyzed.
 '''

# Run with: python -m analysis.analyzeMonthlyMeans-Zonal-QBO
# Then:     python -m plotting.hovmoller_qbo
import pandas as pd
import config
import concurrent.futures
import os
from termcolor import colored

#CONFIGURATION:
pres = 50

#------------------------------

def get_analysis_folder(FAA, WMO, year):
    return config.analysis_folder + str(FAA) + " - " + str(WMO) + "/" + str(year) + "_analysis_ZONAL/"

def get_data_folder(FAA, WMO, year):
    return config.parent_folder + str(FAA) + " - " + str(WMO) + "/" + str(year) + "/"


def empty_monthly_winds(month, year):
    """Return the mandatory pressure grid with NaN winds for one month."""
    avg = filter_pres_bins(None).set_index('pressure', drop=True)
    return avg.add_suffix('_' + str(month) + '_' + str(year))


def filter_pres_bins(df):
    pres_bins = [100., 70., 50., 30., 20.]

    if df is not None:
        #Only keep relevant columns for data analysis.
        df = df[df.columns[df.columns.isin(['pressure', 'speed', 'u_wind', 'v_wind'])]]
        #Some radiosonde flights have duplicate mandatory pressure levels, which creates a weird bug with averaging
        df = df.drop_duplicates(subset=['pressure'])

        #Create empty dataframe to merge filtered values with, in case any pressure values were not recorded by radiosonde
        df2 = pd.DataFrame(columns=['pressure', 'speed', 'u_wind', 'v_wind'])
        df2['pressure'] = pres_bins

        # filter rows of orginial radiosonde flight based on pressure bins
        mask = df['pressure'].isin(pres_bins)
        df3 = df[mask]

        #Create new merged dataframe that has all pressure_bins,  and Nan's for rows not recorded.
        df4 = df2.merge(df3, on='pressure', how='outer', suffixes=('_y', ''))
        df4.drop(df4.filter(regex='_y$').columns, axis=1, inplace=True)
    else:
        df4 = pd.DataFrame(columns=['pressure', 'speed', 'u_wind', 'v_wind'])
        df4['pressure'] = pres_bins

    return df4



def getZonalWinds(year, FAA, WMO):
    data_folder = get_data_folder(FAA, WMO, year)

    avg_list = []
    missing_months = []

    if not os.path.isdir(data_folder):
        print(colored(
            str(FAA) + " - " + str(WMO) + "/" + str(year) +
            " Not Downloaded; filling year with NaN.",
            "yellow",
        ))
        return pd.concat(
            [empty_monthly_winds(month, year) for month in range(1, 13)],
            axis=1,
        )

    for j in range(1, 12 + 1):
        try:
            all_files = os.listdir(data_folder + str(j))
        except FileNotFoundError:
            missing_months.append(j)
            all_files = []
        csv_files = list(filter(lambda f: f.endswith('.csv'), all_files))
        csv_files.sort() #sort the list of CSVs to have the table in the right order

        df_list = []

        #Will need to check if there is missing data.
        if csv_files:
            for csv in csv_files:
                df = pd.read_csv(data_folder + str(j) + "/" + csv, index_col = 0)

                df = filter_pres_bins(df)
                df_list.append(df)

            # Average for the month
            #print("concat", pd.concat(df_list))
            avg = pd.concat(df_list).groupby(level=0).mean() #Double check this does what I think it does
            #print("average",avg)
            avg = avg.set_index('pressure', drop=True)
            avg = avg.add_suffix('_' + str(j) + '_' + str(year))
            avg_list.append(avg)
            #print(avg)

        else:
            avg_list.append(empty_monthly_winds(j, year))
            #print(avg)

    if missing_months:
        print(colored(
            str(FAA) + " - " + str(WMO) + "/" + str(year) +
            " missing months " + ", ".join(map(str, missing_months)) +
            "; filling with NaN.",
            "yellow",
        ))

    avg_annual = pd.concat(avg_list, axis=1)
    return avg_annual


def _get_station_pressure_row(station_index, year, FAA, WMO, pressure):
    """Return one station-year pressure row; safe to call in a worker process."""
    avg_annual = getZonalWinds(year, FAA=FAA, WMO=WMO)
    return station_index, avg_annual.loc[pressure]


def analyze_year(stations_df, year, pressure):
    """Analyze one year sequentially or with the configured process pool."""
    annual_rows = [None] * len(stations_df)

    if config.parallelize:
        num_workers = max(1, min(config.num_workers, len(stations_df)))
        print(colored(
            f"Analyzing {year} in parallel across {num_workers} workers",
            "cyan",
        ))

        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {}
            for i, row in enumerate(stations_df.itertuples(index=False)):
                label = f"{row.FAA} - {row.WMO}"
                future = executor.submit(
                    _get_station_pressure_row,
                    i,
                    year,
                    row.FAA,
                    row.WMO,
                    pressure,
                )
                futures[future] = label

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                label = futures[future]
                try:
                    station_index, pressure_row = future.result()
                except Exception as exc:
                    raise RuntimeError(
                        f"QBO analysis failed for {label}, year {year}"
                    ) from exc

                annual_rows[station_index] = pressure_row
                completed += 1
                print(f"Completed {completed}/{len(stations_df)}: {label} - {year}")
    else:
        print(colored(f"Analyzing {year} sequentially", "cyan"))
        for i, row in enumerate(stations_df.itertuples(index=False)):
            print("Averaging", i, row.WMO, row.FAA, "-", year, "-", pressure)
            station_index, pressure_row = _get_station_pressure_row(
                i,
                year,
                row.FAA,
                row.WMO,
                pressure,
            )
            annual_rows[station_index] = pressure_row

    return pd.DataFrame(annual_rows, index=stations_df.index)

#Main
if __name__=="__main__":
    #continent = config.continent
    #stations_df = pd.read_csv('Radisonde_Stations_Info/CLEANED/' + continent + ".csv")

    continents = ["North_America", "South_America"]
    stations_df = pd.concat(
        [
            pd.read_csv(f"Radiosonde_Stations_Info/CLEANED/{continent}.csv")
            for continent in continents
        ],
        ignore_index=True,
    )
    stations_df = stations_df.drop_duplicates(subset=["WMO"]).reset_index(drop=True)

    stations_df['lat_era5'] = stations_df.apply(lambda x: (-1 * x['  LAT'] if x['N'] == 'S' else 1 * x['  LAT']),
                                                axis=1)
    stations_df['lon_era5'] = stations_df.apply(lambda x: (-1 * x[' LONG'] if x['E'] == 'W' else 1 * x[' LONG']),
                                                axis=1)

    annual_frames = []

    for year in range(config.start_year, config.end_year + 1):
        annual_frame = analyze_year(stations_df, year, pres)
        annual_frames.append(annual_frame)
        print(f"Completed {year}: {len(annual_frame)} stations")

    stations_df_pres = pd.concat([stations_df, *annual_frames], axis=1)
    stations_df_pres.to_csv('QBO-Decadal-Means/stations_df_' + str(pres) + '.csv', index=False)
