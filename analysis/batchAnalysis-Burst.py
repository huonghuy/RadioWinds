from datetime import datetime
import pandas as pd
from termcolor import colored
import numpy as np
import os
from os import listdir
import sys
import traceback

# RadioWinds Imports
import config
import utils
from analysis import opposing_wind_wyoming

"""

The main function at the bottom of this script shows an example of how to analyze all the monthly and annual data
for an individual station in a given year using a list of stations for a continent.

A similar approach could be done to only analyze one station at a time (for instance if colored images are necessary
for only that station) or a custom list of stations.

Run this script until all output text is green.  Recommended to run with the following settings in config:

logging = False
parallelize = True
monthly_export_color = False
annual_export_color = False

"""

def reinitializeProbabilities():
    """
        Reinitialize the wind probabilities dataframe to be empty.

    """

    if config.type == "PRES":
        print(colored(
            "Not setup to work with pressure levels",
            "red"))
        sys.exit()

    if config.type == "ALT":
        column_headers = ["Burst"]

    wind_probabilities = pd.DataFrame(columns=column_headers)

    return wind_probabilities


def burst_monthly_path(FAA, WMO, year, month):
    return os.path.join(
        utils.get_analysis_folder(FAA, WMO, year),
        f"{FAA} - {WMO}-{year}-{month}-BURST.csv",
    )


def burst_monthly_complete(FAA, WMO, year):
    return all(os.path.exists(burst_monthly_path(FAA, WMO, year, month))
               for month in range(1, 13))


def annual_burst_has_data(path):
    if not os.path.exists(path):
        return False
    frame = pd.read_csv(path, index_col=0).apply(pd.to_numeric, errors="coerce")
    return frame.notna().any().any()


def determine_wind_statistics(df, min_alt=15000, max_alt=28000, min_pressure=20, max_pressure=125,
                              alt_step=500, n_sectors=16, speed_threshold=2):

    """
    Determine the wind diversity statistics for an individual radiosonde flight

    :param df: Individual Radiosonde Flight in UofWy Format
    :type df: dataframe
    """

    wind_bins, _ = reinitializeProbabilities()

    if config.type == "ALT":
        df.dropna(subset=['height'], how='all', inplace=True)
        df = df.drop(df[df['height'] < min_alt].index)
        df = df.drop(df[df['height'] > max_alt].index)
        # df = df.drop(df[df['speed'] < 2].index) # we'll add this in later on'
    if config.type == "PRES":
        print(colored(
            "Not setup to work with pressure levels",
            "red"))
        sys.exit()


    return df['height'].max()


def save_wind_probabilties(FAA, WMO, wind_probabilities, analysis_folder, date):
    """
    Saves the opposing wind probabilities for a station a month of radiosonde flights
    """

    wind_probabilities = pd.concat([wind_probabilities, wind_probabilities.apply(['average'])])

    print(colored(
        "Processing Burst data for Station-" + str(FAA) + " - " + str(WMO) +
        " Year-" + str(date.year) + " Month-" + str(date.month),
        "cyan"))


    utils.export_colored_dataframes(wind_probabilities,
                                    title='Monthly Burst Altitudes for Station ' + str(FAA) + " - " + str(WMO) +
                                          ' in Month ' + str(date.month) + ' - ' + str(date.year),
                                    path=analysis_folder,
                                    suffix=str(FAA) + " - " + str(WMO) + "-" + str(date.year) + "-" + str(date.month) + "-BURST",
                                    export_color=config.monthly_export_color)


def anaylze_monthly_data(FAA, WMO, year, min_alt=15000, max_alt=28000, min_pressure=20,
                        max_pressure =125, alt_step=500, n_sectors=16, speed_threshold=2):
    """
        Iterate By [month] for a [station] in a [year]:
            1. Create a new empty wind_probabilties dataframe

            2. Iterate through each [day] within a [Month]:
                i.   getsounding                                  Check if sounding is downloaded.
                ii.  **determine_wind_statistics()**              Anaylze the wind statistics for the individual sounding
                iii. Add probabilities to wind_probabilities df

                df structure:
                * rows: sounding launch time
                * cols: altitude levels
                * data: opposing wind pass case (see opposing_wind_wyoming.py),  0 for no, 1 for yes

            3. **save_wind_probabilties()** save consolidated dataframe of wind probabilties for each [day/rows]
            and [alt_step/columns] and output as a .csv and a colored dataframe image (png) for each month.
    """

    data_folder = utils.get_data_folder(FAA, WMO, year)
    analysis_folder = utils.get_analysis_folder(FAA, WMO, year)

    # Check if monthly sounding data has already been analyzed.  If so, skip
    if burst_monthly_complete(FAA, WMO, year):
        print(colored(
            f"{FAA}-{WMO}/{year} monthly BURST data already analyzed.",
            "green",
        ))
        return True

    # Iterate by month and day for a particular year.
    for j in range (1,12+1):
        # Reinitialize dataframes
        wind_probabilities = reinitializeProbabilities()
        date = datetime(year, j, 1, 0)

        try:
            all_files = os.listdir(data_folder + str(j))
        except:
            print(colored(str(FAA) + " - " + str(WMO) + "/" + str(year) + " Not Downloaded.", "red"))
            return False
            #raise ValueError
        csv_files = list(filter(lambda f: f.endswith('.csv'), all_files))
        csv_files.sort()  # sort the list of CSVs to have the table in the right order

        # Will need to check if there is missing data.
        if csv_files:
            for csv in csv_files:
                df = pd.read_csv(data_folder + str(j) + "/" + csv, index_col = 0)

                #df.dropna(subset=['direction', 'speed'], how='all', inplace=True)

                #wind_probabilities.loc[0] = df['height'].max()


                # Need to check if Dataframe is empty after dropping nan values was done on direction and speed
                try:
                    df.time = pd.to_datetime(df['time'])
                    date = df.time.iat[0]
                    if config.logging:
                        print(date)
                    wind_probabilities.loc[date, "Burst"] = df['height'].max()
                except:
                    print(colored("GOT AN EXCEPTION", "yellow"))
                    pass

        else:
            wind_probabilities.loc[date, :] = np.NAN

            if config.logging:
                print(wind_probabilities)

        save_wind_probabilties(FAA, WMO, wind_probabilities, analysis_folder, date)

    return True


def analyze_annual_data(FAA, WMO, year, min_alt=15000, max_alt=28000,
                        min_pressure=20, max_pressure=125, alt_step=500):

    """
    Check if monthly data has been analyzed. If it has...

    Make a consolidated table of average probabilities at each alt_level for the month and export the data.

    df structure:
        * rows: months
        * cols: altitude levels
        * data: average probabilities
    """
    print("============ANNUAL WIND PROBABILITY ANALYSIS==============\n")

    analysis_folder = utils.get_analysis_folder(FAA, WMO, year)

    files = [f for f in listdir(analysis_folder) if f.endswith("-BURST.csv")]

    annual_probabilities = reinitializeProbabilities()


    for csv in files:
        # read csv for each month of individual station
        try:
            df = pd.read_csv(analysis_folder + csv, index_col=0)

            str_date = df.iloc[0:1].index.values[0]
            date = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')

            annual_probabilities.loc[date.month, :] = df.iloc[-1:].values
        except:
            continue

    annual_probabilities.sort_index(inplace=True, ascending=True)
    print(annual_probabilities)

    # Export the annual charts in the station folder as well, for quicker inspection.
    utils.export_colored_dataframes(annual_probabilities,
                                    title='Monthly Burst Altitudes for Station ' + str(FAA) + " - " + str(
                                        WMO) + ' in ' + str(year),
                                    path=config.analysis_folder + str(FAA) + " - " + str(WMO) + "/",
                                    suffix="analysis_" + str(year) + '-wind_probabilities-BURST',
                                    export_color=config.annual_export_color)


def batch_analysis(year, WMO, FAA, lat, lon, min_alt, max_alt,
            min_pressure, max_pressure, alt_step, n_sectors, speed_threshold):
    """
        Schedule the batch analysis

        1. Analyze all the individual probabilities in a [month] for a [station] in a given [year]
            1a. Export the monthly probabilities
        2. Generate the annual probabilty table from the average [month] wind probabilities
    """
    if config.mode == "era5":
        print(colored("ERA5 forecasts not supported for calm winds batchy analysis", "red"))
        sys.exit()

    if config.mode == "radiosonde":
        monthly_analyzed_status = anaylze_monthly_data(FAA, WMO, year, min_alt=min_alt, max_alt=max_alt,
                                                      min_pressure=min_pressure, max_pressure=max_pressure,
                                                      alt_step=alt_step, n_sectors=n_sectors,
                                                      speed_threshold=speed_threshold)

    # Check if Annual Data for a station and year has already been analyzed by checking if the directory exists.
    annual_path = os.path.join(
        config.analysis_folder,
        str(FAA) + " - " + str(WMO),
        "analysis_" + str(year) + "-wind_probabilities-BURST.csv",
    )
    annual_analyzed_status = annual_burst_has_data(annual_path)

    if not annual_analyzed_status and monthly_analyzed_status:
        analyze_annual_data(FAA, WMO, year, min_alt=min_alt, max_alt=max_alt, min_pressure=min_pressure,
                            max_pressure=max_pressure, alt_step=alt_step)
    print()


def _run_batch_analysis(station_label, year, WMO, FAA, lat, lon, min_alt, max_alt,
                        min_pressure, max_pressure, alt_step, n_sectors, speed_threshold):
    """
    Worker entry point for parallel runs. Surfaces a child-process failure (station
    context + traceback) and re-raises so run_parallel_analysis records it as failed.
    """
    try:
        batch_analysis(year, WMO, FAA, lat, lon, min_alt, max_alt,
                       min_pressure, max_pressure, alt_step, n_sectors, speed_threshold)
    except Exception:
        print(colored(
            "WORKER FAILED for Station " + station_label + " Year-" + str(year) + ":\n" +
            traceback.format_exc(),
            "red"))
        raise


def parallelize(stations_df, year, min_alt, max_alt, min_pressure, max_pressure,
                alt_step, n_sectors, speed_threshold):
    """
    Run batch_analysis for every station via the shared bounded process pool
    (utils.run_parallel_analysis). This variant is radiosonde-only, so workers read
    their own per-station CSVs and need no forecast initializer. Per-station isolation
    means a crash is contained and reported, not silently treated as success.
    """
    tasks = []
    for row in stations_df.itertuples(index=False):
        station_label = str(row.FAA) + " - " + str(row.WMO)
        tasks.append((station_label,
                      (station_label, year, row.WMO, row.FAA, row.lat_era5, row.lon_era5,
                       min_alt, max_alt, min_pressure, max_pressure, alt_step,
                       n_sectors, speed_threshold)))

    return utils.run_parallel_analysis(_run_batch_analysis, tasks,
                                       num_workers=config.num_workers)


if __name__ == "__main__":

    continent = config.continent
    stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv")
    # stations_df = stations_df.loc[stations_df["CO"] == "US"]  # Only do US Countries for now
    # stations_df = stations_df[-1:]

    # Check if ERA5 forecast date range matches config file
    # Maybe later check if The coordinates are right?

    # This variant is radiosonde-only; ERA5 forecasts are not supported. Refuse the
    # mode up front: the per-station batch_analysis would otherwise sys.exit() inside
    # a pool worker, raising SystemExit, which the driver's "except Exception" can't
    # catch.
    if config.mode == "era5":
        print(colored("ERA5 mode is not supported by this variant (radiosonde only).", "red"))
        sys.exit()

    stations_df['lat_era5'] = stations_df.apply(lambda x: (-1 * x['  LAT'] if x['N'] == 'S' else 1 * x['  LAT']), axis=1)
    stations_df['lon_era5'] = stations_df.apply(lambda x: (-1* x[' LONG'] if x['E'] == 'W' else 1 * x[' LONG']), axis=1)

    print(stations_df)

    # Initialize Variables
    min_alt = config.min_alt
    max_alt = config.max_alt
    min_pressure = config.min_pressure
    max_pressure = config.max_pressure
    alt_step = config.alt_step
    n_sectors = config.n_sectors
    speed_threshold = config.speed_threshold

    # DO THE WIND PROBABILTIES ANALYSIS
    for year in range(config.start_year, config.end_year + 1):

        if config.parallelize:
            print(colored(
                "============================================================================================\n" +
                "==========Analyzing Radiosonde Datasets for YEAR - " + str(year) +
                " in Parallel [Multiprocessing]========\n" +
                "============================================================================================\n",
                "cyan"))
            parallelize(stations_df, year=year,
                        min_alt=config.min_alt,
                        max_alt=config.max_alt,
                        min_pressure=config.min_pressure,
                        max_pressure=config.max_pressure,
                        alt_step=config.alt_step,
                        n_sectors=config.n_sectors,
                        speed_threshold=config.speed_threshold)

        else:
            print(colored(
                "============================================================================================\n" +
                "=================Analyzing Radiosonde Datasets for YEAR - " + str(year) +
                " in Sequence==================\n" +
                "============================================================================================\n",
                "cyan"))
            for row in stations_df.itertuples(index=False):
                batch_analysis(year,
                        WMO=row.WMO,
                        FAA=row.FAA,
                        lat=row.lat_era5,
                        lon=row.lon_era5,
                        min_alt=config.min_alt,
                        max_alt=config.max_alt,
                        min_pressure=config.min_pressure,
                        max_pressure=config.max_pressure,
                        alt_step=config.alt_step,
                        n_sectors=config.n_sectors,
                        speed_threshold=config.speed_threshold)
