import os
from termcolor import colored

import sys
sys.path.append('../RadioWinds')
import config

'''
This checks if the Radiosondes Directory Downloads are organized correctly By Station, Year, and Months.  
If Months are missing the program will report red text of the missing months.  
You can try redownloading the months or adding empty months for missing data from the server.

If the radisonde downloads are organized correctly, this program does not print anything. 
'''

def inspect_downloads(parent_folder, check_total_soundings=False):
    """Validate station/year/month layout while ignoring completion markers."""
    number_of_stations = 0
    number_of_soundings = 0

    for station in sorted(os.listdir(parent_folder)):
        station_path = os.path.join(parent_folder, station)
        if not os.path.isdir(station_path):
            continue
        number_of_stations += 1

        for year in sorted(os.listdir(station_path)):
            year_path = os.path.join(station_path, year)
            if not os.path.isdir(year_path):
                continue

            months = [
                name
                for name in os.listdir(year_path)
                if name.isdigit()
                and 1 <= int(name) <= 12
                and os.path.isdir(os.path.join(year_path, name))
            ]
            if len(months) != 12:
                print(colored((station, year, len(months)), "red"))

            if check_total_soundings:
                for month in months:
                    month_path = os.path.join(year_path, month)
                    number_of_soundings += sum(
                        name.endswith(".csv") for name in os.listdir(month_path)
                    )

    return number_of_stations, number_of_soundings


def main():
    number_of_stations, number_of_soundings = inspect_downloads(
        config.parent_folder,
        check_total_soundings=False,
    )
    print("Total Number of Stations Downloaded ", number_of_stations)
    if number_of_soundings:
        print("Total Number of Soundings Downloaded ", number_of_soundings)


if __name__ == "__main__":
    main()
