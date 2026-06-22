from siphonMulti import SiphonMulti
import pandas as pd
import os
from termcolor import colored
from pathlib import Path
from multiprocessing import Process, Manager
import config
import utils
import sys

"""
This script batch downloads every radiosonde file (one month at a time, and 
then parsing into individual flights .csv's). 

.. note:: 
        This script takes a while to run (up to an hour) depending on how many 
        stations and years are being downloaded

.. tip:: 
        If the download script hangs:
            *End it
            * run checkRadiosondeDownload.py
            * Delete any [year] folders for that station that output red text
            * Run again    
        
.. important:: 
        Currently, this script checks to see if a year folder already exists for the
        desired station and moves on if the folder exists. 
        
        Therefore, this script needs to be run in full to garuntee there's no missing
        or incompletely downloaded months.

Make sure to set the following variables in config before running:
* parent_dir
* parent_folder
* continent
* parallelize
* start_year
* end_year

"""


def save_monthly_soundings(df_monthly_list, FAA, WMO, year, month):
    """
    Export a list of monthly radiosonde dataframes into individual CSVs in the data_folder
    specified in config.

    This function exports 1 month at a time.
    """

    data_folder_month = utils.get_data_folder(FAA, WMO, year) + str(month) + "/"

    # New month folders are made, if they don't exist,  even if there's no radiosonde data to put inside
    # in order to keep a standard format across all stations with varying data drop out periods over the months/years.
    isExist = os.path.exists(data_folder_month)
    if not isExist:
        os.makedirs(data_folder_month)

    if df_monthly_list is not None:
        for df in df_monthly_list:
            date = df.time[0]

            filepath_sounding = Path(data_folder_month + str(FAA) + "-" + str(date.year) + "-" + str(
                date.month) + "-" + str(date.day) + "-" + str(date.hour) + '.csv')
            filepath_sounding.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(filepath_sounding)


def get_yearly_soundings(FAA, WMO, year):
    """
    Download all soundings for a station in a given year one month at a time.

    Parallelizing this function in config downloads multiple stations simultaenously and greatly speeds up performance.

    :param FAA: FAA Radiosonde Station Identifier (3 to 4 character code)
    :type FAA: string
    :param WMO: WMO Radiosonde Station Identifier (5 digit code)
    :type WMO: int
    :param year: Year
    :type year: int

    """
    #Check if Soundings Data Folder exists:

    data_folder = utils.get_data_folder(FAA, WMO, year)

    # Check if the soundings have already been downloaded.
    # not checking incomplete downloads yet.
    isExist = os.path.exists(data_folder)
    if isExist:
        print(colored("Soundings for " + str(FAA) + " - " + str(FAA) + " - " + str(WMO) + " in " + str(
            year) + " are downloaded locally", "green"))

    else:
        print(colored("Soundings for " + str(FAA) + " - " + str(FAA) + " - " + str(WMO) + " in " + str(
            year) + " are not downloaded locally. \n Will continue to download for offline analysis", "yellow"))

        yearly_count = 0
        # Iterate by Month
        for i in range(1,12+1):

            df_monthly_list = None
            count = 0
            missing_data = False

            while df_monthly_list is None:
                try:
                    # If everything goes smooth
                    # A list of radiosonde dataframes will be returned for a given moth
                    df_monthly_list = SiphonMulti.request_data(year=year, month=i, site_id=WMO)
                except ValueError as ve:
                    # I have never seen this error actually trigger with monthly downloads, only
                    # individual sounding downloads in the standard siphon.
                    print(colored(ve, "red"))
                    missing_data = True
                    # df = pd.DataFrame()
                    pass
                except:
                    # Sometimes the webserver at university of Wyoming Hangs.  But it almost always resolves eventually.
                    # Keep trying until the data is downloaded.
                    # The highest server error I've seen is 500.  The warning message shows which station is hanging for
                    # individual download if necessary.
                    count += 1
                    # df = None
                    if count % 50 == 0:
                        print("SERVER ERRORS", count, "TRIES - ", FAA, WMO, "month", i)
                        missing_data = True

            save_monthly_soundings(df_monthly_list, FAA, WMO, year, month = i)

            if not missing_data:
                result = ('Number of Monthly Soundings for '
                          '{FAA}/{WMO} in {month}/{year} is {num_of_soundings}').format(FAA=FAA, WMO = WMO, year = year, month = i, num_of_soundings = len(df_monthly_list))

                if config.logging:
                    print(result)
                # Always log yearly count
                yearly_count += len(df_monthly_list)

        print("Total number of annual soundings download for", FAA, "-", WMO, "in", year, ":", yearly_count)


def parallelize(stations_df, year):
    """
    Parralelize the download process for each station one year at a time.  Each station is sent to it's own process to download radiosonde flights
    for the year.

    This makes the bulk download of radiosonde data for a list of stations for a year, go much faster.

    It's recommenmded to turn logging off in config if activating this function
    """
    try:
        queue = Manager().Queue()
        procs = [Process(target=get_yearly_soundings, args=(row.FAA, row.WMO, year)) for row in stations_df.itertuples(index=False)]
        for p in procs: p.start()
        for p in procs: p.join()

        results = []
        while not queue.empty():
            results.append(queue.get)

        return results

    # If There's a keyboard interrupt, terminate multiprocessing in Python, and exit program
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, terminating worker processes.")
        for p in procs: p.terminate()
        sys.exit()


if __name__ == "__main__":

    if config.continent == "All":
        continents = ["North_America", "South_America", "Europe",
                      "Asia", "Africa", "Australia", "Antarctica"]
    else:
        continents = [config.continent]
        
    for continent in continents:
        print(colored("=== Starting continent: " + continent + " ===", "cyan"))
        stations_df = pd.read_csv('Radiosonde_Stations_Info/CLEANED/' + continent + ".csv")
        print(stations_df)

        for i in range(config.start_year, config.end_year + 1):
            if config.parallelize:
                print(colored("Downloading Radiosonde Datasets in Parallel [Multiprocessing]", "cyan"))
                parallelize(stations_df, year=i)
            else:
                print(colored("Downloading Radiosonde Datasets in Sequence", "cyan"))
                for row in stations_df.itertuples(index=False):
                    get_yearly_soundings(row.FAA, row.WMO, year=i)
            print(colored("MOVING ON TO YEAR " + str(i), "cyan"))
