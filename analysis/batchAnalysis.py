from datetime import datetime
import pandas as pd
from termcolor import colored
import numpy as np
import os
from os import listdir
import sys
from multiprocessing import Process, Manager
import copy

# RadioWinds Imports
import config
import utils
from analysis import opposing_wind_wyoming
from analysis.Forecast import Forecast

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
        wind_bins = config.era5_pressure_levels[::-1]
        wind_bins = wind_bins[(wind_bins <= config.max_pressure)]
        wind_bins = wind_bins[(wind_bins >= config.min_pressure)]
        # print(wind_bins)
    if config.type == "ALT":
        wind_bins = np.arange(config.min_alt, config.max_alt, config.alt_step)

    # print("wind bins", wind_bins)

    if config.type == "ALT":
        column_headers = np.char.mod("%.1f", wind_bins / 1000.)
    if config.type == "PRES":
        pressure_bins = wind_bins
        column_headers = np.char.mod("%.1f", pressure_bins)

    wind_probabilities = pd.DataFrame(columns=column_headers)

    return wind_bins, wind_probabilities


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
        df = df.drop(df[df['pressure'] < min_pressure].index)
        df = df.drop(df[df['pressure'] > max_pressure].index)

    # Determine Wind Statistics
    opposing_wind_directions, opposing_wind_levels = opposing_wind_wyoming.determine_opposing_winds(df,
                                                                                                    wind_bins=wind_bins,
                                                                                                    n_sectors=n_sectors,
                                                                                                    speed_threshold=speed_threshold)
    calm_winds = opposing_wind_wyoming.determine_calm_winds(df, alt_step=alt_step)
    full_winds = opposing_wind_wyoming.determine_full_winds(df, wind_bins=wind_bins, speed_threshold=speed_threshold)

    if config.logging:
        opposing_wind_wyoming.print_wind_statistics(opposing_wind_directions, opposing_wind_levels,
                                                    calm_winds, full_winds)

    return wind_bins, opposing_wind_levels


def add_average_row(df):
    averages = []
    for column in df.columns:
        not_nan_count = df[column].notna().sum()
        if not_nan_count >= len(df) / 2:
            column_average = df[column].mean()
        else:
            column_average = np.nan
        averages.append(column_average)
    df.loc['average'] = averages
    return df


def save_wind_probabilties(FAA, WMO, wind_probabilities, analysis_folder, date):
    """
    Saves the opposing wind probabilities for a station a month of radiosonde flights
    """

    #Sort datetime index in ascending order
    wind_probabilities = wind_probabilities.sort_index()

    #apply an average to the end of the table, for opposing wind probabilities at each altitude level
    #wind_probabilities = pd.concat([wind_probabilities, wind_probabilities.apply(['average'], skipna=False)])

    #wind_probabilities.loc["average"] = wind_probabilities.mean(axis=0)

    #wind_probabilities.loc["nan"] = wind_probabilities.isnull().sum(axis=0)

    wind_probabilities = add_average_row(wind_probabilities)

    print(colored(
        "Processing data for Station-" + str(FAA) + " - " + str(WMO) +
        " Year-" + str(date.year) + " Month-" + str(date.month),
        "cyan"))


    utils.export_colored_dataframes(wind_probabilities,
                                    title='Opposing Wind Probabilities for Station ' + str(FAA) + " - " + str(WMO) +
                                          ' in Month ' + str(date.month) + ' ' + str(date.year),
                                    path=analysis_folder,
                                    suffix=str(FAA) + " - " + str(WMO) + "-" + str(date.year) + "-" + str(date.month),
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
    if utils.check_analyzed(FAA, WMO, year,
                            path=utils.get_analysis_folder(FAA, WMO, year),
                            category="monthly"):
        return True

    # Iterate by month and day for a particular year.
    for j in range (1,12+1):
        # Reinitialize dataframes
        wind_bins, wind_probabilities = reinitializeProbabilities()

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

                df.dropna(subset=['direction', 'speed'], how='all', inplace=True)

                wind_bins, opposing_wind_levels = determine_wind_statistics(df, min_alt=min_alt,
                                                                            max_alt=max_alt,
                                                                            min_pressure=min_pressure,
                                                                            max_pressure=max_pressure,
                                                                            alt_step=alt_step,
                                                                            n_sectors=n_sectors,
                                                                            speed_threshold=speed_threshold)

                # There's probably a faster way to do this with numpy.
                # Or maybe I should change the output of opposing_wind_levels?
                mask = copy.deepcopy(wind_bins)
                for k in range(len(mask)):
                    if wind_bins[k] in opposing_wind_levels:
                        mask[k] = 1
                    else:
                        mask[k] = 0




                try:
                    # Determine index values of missing data for PRessure and altitude in case of early burst
                    difference_array = np.absolute(wind_bins - df['pressure'].min())
                    min_pres_index = difference_array.argmin()

                    max_alt_index = ((df['height'].max() - config.min_alt) / config.alt_step)
                    max_alt_index = int(max_alt_index) + 1

                    mask = mask.astype(float)

                    # If balloon pops before minimum altitude, then entire row is nan
                    if max_alt_index < 0:
                        mask[:] = np.NAN
                    # Otherwise fill in nan values for the indecies with missing values
                    else:
                        if config.type == "ALT":
                            for i in range(max_alt_index,len(mask)):
                                mask[i] = np.NAN
                        if config.type == "PRES":
                            for i in range(0,min_pres_index):
                                mask[i] = np.NAN

                except:
                    print(colored("MASKING EXCEPTION", "yellow"))

                # Need to check if Dataframe is empty after dropping nan values was done on direction and speed
                try:
                    df.time = pd.to_datetime(df['time'])
                    date = df.time.iat[0]
                    if config.logging:
                        print(date)
                    wind_probabilities.loc[date, :] = mask
                except:
                    print(colored("GOT AN EXCEPTION", "yellow"))
                    pass

        else:
            date = datetime(year, j, 1, 00)  # day and time shouldn't matter
            mask = np.empty(len(wind_bins))
            mask[:] = np.nan
            wind_probabilities.loc[date, :] = mask

            if config.logging:
                print(wind_probabilities)

        if config.type == "PRES":
            # Reverse order of dataframes for pressure, since high pressure = low altitude
            wind_probabilities = wind_probabilities.iloc[:, ::-1]

        save_wind_probabilties(FAA, WMO, wind_probabilities, analysis_folder, date)

    return True


def anaylze_monthly_data_era5(era5, lat, lon, FAA, WMO, year, min_alt=15000, max_alt=28000,
                             min_pressure=20, max_pressure=125, alt_step=500, n_sectors=16, speed_threshold=2):
    """
    Very similar to the function above, with some slight tweaks to use an ERA5 forecast instead of Radiosonde data.
    """

    current_month = 1

    analysis_folder = utils.get_analysis_folder(FAA, WMO, year)

    # Reinitialize dataframes
    wind_bins, wind_probabilities = reinitializeProbabilities()

    # Check if monthly sounding data has already been analyzed.  If so, skip
    if utils.check_analyzed(FAA, WMO, year,
                            path=utils.get_analysis_folder(FAA, WMO, year),
                            category="monthly"):
        return True

    for time in era5.time_convert:
        station = era5.get_station(time, lat, lon)

        month = time.month
        day = time.day
        hour = time.hour

        station.dropna(subset=['direction', 'speed'], how='all', inplace=True)

        wind_bins, opposing_wind_levels = determine_wind_statistics(station, min_alt=min_alt, max_alt=max_alt,
                                                                    min_pressure=min_pressure, max_pressure=max_pressure,
                                                                    alt_step=alt_step, n_sectors=n_sectors,
                                                                    speed_threshold=speed_threshold)

        if config.logging:
            print("opposing_wind_levels", opposing_wind_levels)
        # Double check this when full forecast is downloaded

        # Do I need to do this again?
        if month != current_month or (month == 12 and day== 31 and hour == 12):
            if config.logging:
                print(wind_probabilities)
            save_wind_probabilties(FAA, WMO, wind_probabilities, analysis_folder, date)
            current_month += 1

            # reinitialize dataframes
            wind_bins, wind_probabilities = reinitializeProbabilities()

        # there's probably a faster way to do this with numpy.
        # Or maybe I should change the output of opposing_wind_levels?
        mask = wind_bins
        for k in range(len(mask)):
            if wind_bins[k] in opposing_wind_levels:
                mask[k] = 1
            else:
                mask[k] = 0

        # Need to check if Dataframe is empty after dropping nan values was done on direction and speed

        # station.time = station['time']
        date = station.time.iat[0]
        if config.logging:
            print()
            print(date)
        wind_probabilities.loc[date, :] = mask

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

    files = [f for f in listdir(analysis_folder) if f.endswith(".csv")]

    wind_bins, annual_probabilities = reinitializeProbabilities()

    #Reverse order of column headers, since monthly probabilities already took care of that.  Don't want to reverse twice.
    if config.type == "PRES":
        # Reverse order of dataframes for pressure, since high pressure = low altitude
        annual_probabilities = annual_probabilities.iloc[:, ::-1]


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
                                    title='Opposing Wind Probabilities for Station ' + str(FAA) + " - " + str(
                                        WMO) + ' 12Z in ' + str(year),
                                    path=config.analysis_folder + str(FAA) + " - " + str(WMO) + "/",
                                    suffix="analysis_" + str(year) + '-wind_probabilities-TOTAL',
                                    export_color=config.annual_export_color)


def batch_analysis(era5, year, WMO, FAA, lat, lon, min_alt, max_alt,
            min_pressure, max_pressure, alt_step, n_sectors, speed_threshold):
    """
        Schedule the batch analysis

        1. Analyze all the individual probabilities in a [month] for a [station] in a given [year]
            1a. Export the monthly probabilities
        2. Generate the annual probabilty table from the average [month] wind probabilities
    """
    if config.mode == "era5":
        monthly_analyzed_status = anaylze_monthly_data_era5(era5, lat, lon, FAA, WMO, year,
                                                           min_alt, max_alt, min_pressure, max_pressure,
                                                           alt_step, n_sectors, speed_threshold)

    if config.mode == "radiosonde":
        monthly_analyzed_status = anaylze_monthly_data(FAA, WMO, year, min_alt=min_alt, max_alt=max_alt,
                                                      min_pressure=min_pressure, max_pressure=max_pressure,
                                                      alt_step=alt_step, n_sectors=n_sectors,
                                                      speed_threshold=speed_threshold)

    # Check if Annual Data for a station and year has already been analyzed by checking if the directory exists.
    annual_analyzed_status = utils.check_analyzed(FAA, WMO, year,
                                                  path=utils.get_analysis_folder(FAA, WMO, year)[:-14] + "analysis_" +
                                                                                 str(year) + '-wind_probabilities-TOTAL.csv',
                                                  category="annual")

    if not annual_analyzed_status and monthly_analyzed_status:
        analyze_annual_data(FAA, WMO, year, min_alt=min_alt, max_alt=max_alt, min_pressure=min_pressure,
                            max_pressure=max_pressure, alt_step=alt_step)
    print()


def parallelize(era5, stations_df, year,min_alt,max_alt,min_pressure,max_pressure,alt_step,n_sectors,speed_threshold):
    """
    Parrallelize the analysis process.  Each station downlaod goes on it's own thread.
    Activating this functionality makes the analysis much faster.
    If debugging new/added features, don't use parallelize.
    """

    try:
        queue = Manager().Queue()
        procs = [Process(target=batch_analysis, args=(era5, year, row.WMO, row.FAA, row.lat_era5, row.lon_era5,
                                               min_alt, max_alt, min_pressure, max_pressure, alt_step,
                                               n_sectors,speed_threshold))
                                               for row in stations_df.itertuples(index=False)]
        for p in procs: p.start()
        for p in procs: p.join()

        results = []
        while not queue.empty():
            results.append(queue.get)

        return results

    # If There's a keyboard interrupt, terminate multiprocessing in Python, and exit program
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, terminating workers")
        for p in procs: p.terminate()
        sys.exit()


if __name__ == "__main__":

    continent = config.continent
    stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv")
    # stations_df = stations_df.loc[stations_df["CO"] == "US"]  # Only do US Countries for now
    # stations_df = stations_df[-1:]

    # Check if ERA5 forecast date range matches config file
    # Maybe later check if The coordinates are right?

    era5 = None # Is this right? Keep as None for now when not using era5 forecast

    if config.mode == "era5":
        #Initialize forecast reader (handles both GFS- and ERA5-sourced files)
        era5 = Forecast.from_file(config.forecast['file'])
        start_datetime, end_datetime = era5.get_statistics()

        if start_datetime != datetime(config.start_year, 1, 1, 00):
            print(colored("Dates mismatch for analysis. ERA5 start date is " + str(start_datetime) + ". Config file is " +
                          str(datetime(config.start_year, 1, 1, 00)) , "red"))
            sys.exit()

        if end_datetime != datetime(config.end_year, 12, 31, 12):
            print(colored(
                "Dates mismatch for analysis. ERA5 start date is " + str(end_datetime) + ". Config file is " + str(
                    datetime(config.end_year, 12, 31, 12)), "red"))
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
                " in Parallel [MultiThreading]========\n" +
                "============================================================================================\n",
                "cyan"))
            parallelize(era5, stations_df, year=year,
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
                batch_analysis(era5, year,
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
