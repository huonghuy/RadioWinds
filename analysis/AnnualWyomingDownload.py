from siphonMulti import SiphonMulti
import calendar
from datetime import date, datetime, timezone
import pandas as pd
from termcolor import colored
from pathlib import Path
import traceback
import config
import utils

"""
This script batch downloads every radiosonde file (one month at a time, and 
then parsing into individual flights .csv's). 

.. note:: 
        This script takes a while to run (up to an hour) depending on how many 
        stations and years are being downloaded

Interrupted downloads can be rerun safely. Completed months are skipped, failed
months are retried, and a year is marked complete only after all twelve months
finish successfully.

.. tip::
        If the process is interrupted or Wyoming temporarily fails, rerun this
        script normally. Do not delete the year folder: completed months will be
        skipped and only incomplete months will be requested again.

.. important::
        Hidden ``.download_in_progress`` and ``.download_complete`` marker files
        distinguish interrupted, empty, and completed months. Existing datasets
        created before these markers were introduced remain supported.

Make sure to set the following variables in config before running:
* parent_dir
* parent_folder
* continent
* parallelize
* start_year
* end_year

"""

# Completion markers make an empty month unambiguous: an empty directory with a
# complete marker means the server was queried successfully but returned no data.
COMPLETE_MARKER = ".download_complete"
IN_PROGRESS_MARKER = ".download_in_progress"


def _month_is_complete(month_folder, legacy_layout=False):
    """Return whether a month is complete, upgrading legacy CSV folders."""
    month_folder = Path(month_folder)

    # An interrupted write always takes precedence over any CSVs left behind.
    if (month_folder / IN_PROGRESS_MARKER).exists():
        return False
    if (month_folder / COMPLETE_MARKER).exists():
        # Early Siphon 0.11 downloads used release hours (usually 11/23) in
        # filenames. Treat them as incomplete so a rerun replaces them with the
        # nominal 00/12 synoptic-cycle convention used throughout RadioWinds.
        for csv_file in month_folder.glob("*.csv"):
            try:
                hour = int(csv_file.stem.rsplit("-", 1)[1])
            except (IndexError, ValueError):
                return False
            if hour not in (0, 6, 12, 18):
                return False
        return True

    # Older downloads have CSVs but no marker. Mark these as complete when the
    # surrounding year is recognized as a legacy layout so they are not fetched again.
    if legacy_layout and any(month_folder.glob("*.csv")):
        (month_folder / COMPLETE_MARKER).touch()
        return True
    return False


def _year_is_complete(data_folder):
    """Recognize explicit completion and fully populated legacy year folders."""
    data_folder = Path(data_folder)
    month_folders = [data_folder / str(month) for month in range(1, 13)]

    # Recheck month filenames even when a year marker exists so early Siphon 0.11
    # 11/23 release-time downloads are automatically migrated on the next run.
    if (data_folder / COMPLETE_MARKER).exists():
        return all(_month_is_complete(folder) for folder in month_folders)

    # A current-format year is complete only when all month markers exist.
    if any((folder / IN_PROGRESS_MARKER).exists() for folder in month_folders):
        return False
    if any((folder / COMPLETE_MARKER).exists() for folder in month_folders):
        return all((folder / COMPLETE_MARKER).exists() for folder in month_folders)

    # Backward compatibility: the old downloader considered a year complete once
    # all twelve month directories had been created, including valid empty months.
    return all(folder.is_dir() for folder in month_folders)


def _utc_today():
    """Return the UTC date separately so current-year behavior is testable."""
    return datetime.now(timezone.utc).date()


def save_monthly_soundings(df_monthly_list, FAA, WMO, year, month,
                           mark_complete=True):
    """
    Export a list of monthly radiosonde dataframes into individual CSVs in the data_folder
    specified in config.

    This function exports 1 month at a time.
    """

    data_folder_month = Path(utils.get_data_folder(FAA, WMO, year)) / str(month)

    # Always create the month folder, even for a valid month with no soundings, to
    # retain the project's standard year/month directory structure.
    data_folder_month.mkdir(parents=True, exist_ok=True)
    in_progress = data_folder_month / IN_PROGRESS_MARKER

    # The network request finishes before this function is called, so it is safe
    # to replace the month's CSV set. This clears interrupted files and older
    # 11/23 release-time filenames before writing normalized synoptic filenames.
    for previous_csv in data_folder_month.glob("*.csv"):
        previous_csv.unlink()
    in_progress.touch()

    # SiphonMulti returns one dataframe per sounding with time normalized to its
    # nominal synoptic cycle; release_time retains the actual balloon release.
    if df_monthly_list is not None:
        for df in df_monthly_list:
            date = df.time[0]

            filepath_sounding = data_folder_month / (str(FAA) + "-" + str(date.year) + "-" + str(
                date.month) + "-" + str(date.day) + "-" + str(date.hour) + '.csv')
            filepath_sounding.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(filepath_sounding)

    # A current, still-growing month is saved but deliberately left incomplete so
    # a later run refreshes it with newly available launches.
    complete_marker = data_folder_month / COMPLETE_MARKER
    if mark_complete:
        complete_marker.touch()
    else:
        complete_marker.unlink(missing_ok=True)
    in_progress.unlink()


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
    data_folder = Path(utils.get_data_folder(FAA, WMO, year))
    today = _utc_today()

    # Only past years can be permanently complete. A current-year marker from an
    # older run is ignored so the current month can continue accumulating data.
    if year < today.year and _year_is_complete(data_folder):
        print(colored("Soundings for " + str(FAA) + " - " + str(FAA) + " - " + str(WMO) + " in " + str(
            year) + " are downloaded locally", "green"))
        return

    print(colored("Soundings for " + str(FAA) + " - " + str(FAA) + " - " + str(WMO) + " in " + str(
        year) + " are incomplete locally. \n Will continue downloading missing months", "yellow"))

    month_folders = [data_folder / str(month) for month in range(1, 13)]

    # This value is intentionally determined once. As legacy months are upgraded
    # with markers during this run, the remaining legacy months must still be skipped.
    legacy_layout = not any(
        (folder / COMPLETE_MARKER).exists()
        or (folder / IN_PROGRESS_MARKER).exists()
        for folder in month_folders
    )
    yearly_count = 0
    failed_months = []
    pending_months = []

    # Work month-by-month so a rerun can skip successful work instead of starting
    # the station/year again from January.
    for month, month_folder in enumerate(month_folders, start=1):
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Future months are expected pending work, not download failures.
        if first_day > today:
            pending_months.append(month)
            continue

        month_complete = last_day < today
        if month_complete and _month_is_complete(
                month_folder, legacy_layout=legacy_layout):
            # Include existing files so the final annual count covers resumed months.
            yearly_count += len(list(month_folder.glob("*.csv")))
            continue

        try:
            # SiphonMulti handles timestamp-level missing data and transient retries.
            df_monthly_list = SiphonMulti.request_data(
                year=year, month=month, site_id=WMO
            )
            save_monthly_soundings(
                df_monthly_list, FAA, WMO, year, month,
                mark_complete=month_complete,
            )
        except Exception as exc:
            # Continue later months, then surface one summary failure to the station worker.
            failed_months.append((month, exc))
            print(colored(
                f"DOWNLOAD FAILED for {FAA} - {WMO} in {year} month {month}: {exc!r}",
                "red",
            ))
            continue

        yearly_count += len(df_monthly_list)
        if not month_complete:
            pending_months.append(month)
        if config.logging:
            print(
                f"Number of Monthly Soundings for {FAA}/{WMO} in "
                f"{month}/{year} is {len(df_monthly_list)}"
            )

    print("Total number of annual soundings downloaded for", FAA, "-", WMO, "in", year, ":", yearly_count)

    if failed_months:
        months = ", ".join(str(month) for month, _exc in failed_months)
        raise RuntimeError(
            f"Station {FAA} - {WMO} failed for {year} month(s): {months}. "
            "Rerun to resume those months."
        ) from failed_months[0][1]

    if pending_months:
        months = ", ".join(str(month) for month in pending_months)
        print(colored(
            f"Year {year} remains partial; pending/current month(s): {months}",
            "yellow",
        ))
        return

    # The year marker is created only when all twelve months completed successfully.
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / COMPLETE_MARKER).touch()

def _run_yearly_soundings(station_label, FAA, WMO, year):
    """
    Worker entry point for parallel runs.

    Wraps get_yearly_soundings so a failure inside a child process is surfaced 
    (station context + full traceback) and then re-raised, so run_parallel_analysis 
    records it as a failed task.
    """
    try:
        get_yearly_soundings(FAA, WMO, year)
    except Exception:
        print(colored(
            "WORKER FAILED for Station " + station_label + " Year-" + str(year) + ":\n" +
            traceback.format_exc(),
            "red"))
        raise

def parallelize(stations_df, year):
    """
    Parralelize the download process for each station one year at a time.
    Uses the shared utils.run_parallel_analysis bounded process pool.
    """
    tasks = []
    for row in stations_df.itertuples(index=False):
        station_label = str(row.FAA) + " - " + str(row.WMO)
        tasks.append((station_label, (station_label, row.FAA, row.WMO, year)))

    return utils.run_parallel_analysis(_run_yearly_soundings, tasks,
                                       num_workers=config.num_workers)

if __name__ == "__main__":

    if config.continent == "All":
        station_directory = Path("Radiosonde_Stations_Info/CLEANED")
        continents = sorted(path.stem for path in station_directory.glob("*.csv"))
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
