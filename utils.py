import pandas as pd
import config
import dataframe_image as dfi
from pathlib import Path
import os
import sys
import tempfile
import concurrent.futures
from termcolor import colored
import glob
import numpy as np

"""
utils.py contains multiple helper and utility functions that are used across multiple other scripts in RadioWinds.
"""

def prompt_continue_or_exit(prompt):
    """Single-keypress confirm: Enter continues, any other key exits.

    Reads one raw keypress so the user doesn't have to press Enter twice.
    Falls back to line-based input() when stdin isn't an interactive tty
    (piped input / CI), where a bare Enter (empty line) continues and any
    other text exits. Returns True to continue, False to exit.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()

    try:
        import termios, tty
    except ImportError:
        termios = None

    if termios is not None and sys.stdin.isatty():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\n")
        sys.stdout.flush()
        # Enter arrives as \r (or \n) in raw mode; any other key (space, etc.) exits.
        return ch in ("\r", "\n")

    # Non-interactive fallback: empty line continues, anything else exits.
    try:
        return input().strip() == ""
    except EOFError:
        return False


def lookupWMO(FAA):
    path = r'Radiosonde_Stations_Info/CLEANED/'  # use your path
    all_stations = glob.glob(os.path.join(path, "*.csv"))

    df = pd.concat((pd.read_csv(f) for f in all_stations), ignore_index=True)
    df = df.drop_duplicates(subset=['WMO'])

    df = df.drop_duplicates()

    return df.loc[df['FAA'] == FAA]['WMO'].iloc[0]

def lookupStationName(FAA):
    path = r'Radiosonde_Stations_Info/CLEANED/'  # use your path
    all_stations = glob.glob(os.path.join(path, "*.csv"))

    df = pd.concat((pd.read_csv(f) for f in all_stations), ignore_index=True)
    df = df.drop_duplicates(subset=['WMO'])

    df = df.drop_duplicates()

    return df.loc[df['FAA'] == FAA]['Station_Name'].iloc[0]

def lookupCountry(FAA):
    path = r'Radiosonde_Stations_Info/CLEANED/'  # use your path
    all_stations = glob.glob(os.path.join(path, "*.csv"))

    df = pd.concat((pd.read_csv(f) for f in all_stations), ignore_index=True)
    df = df.drop_duplicates(subset=['WMO'])

    df = df.drop_duplicates()

    return df.loc[df['FAA'] == FAA]['CO'].iloc[0]

def lookupCoordinate(FAA):
    '''
    This is just for looking up radiosonde coordinates
    :param FAA:
    :return:
    '''
    path = r'Radiosonde_Stations_Info/CLEANED/'  # use your path
    all_stations = glob.glob(os.path.join(path, "*.csv"))

    df = pd.concat((pd.read_csv(f) for f in all_stations), ignore_index=True)
    df = df.drop_duplicates(subset=['WMO'])

    df = df.drop_duplicates()

    df = convert_stations_coords(df)

    #Hard coded for Western Hemisphere Right nowe
    return df.loc[df['FAA'] == FAA]['lat_era5'].iloc[0] , df.loc[df['FAA'] == FAA]['lon_era5'].iloc[0], df.loc[df['FAA'] == FAA]['EL'].iloc[0]


def getWorldStations():
    path = r'Radiosonde_Stations_Info/CLEANED/'  # use your path
    all_stations = glob.glob(os.path.join(path, "*.csv"))

    df = pd.concat((pd.read_csv(f,  index_col=1) for f in all_stations))
    #df = df.drop_duplicates(subset=['WMO'])

    return df

def convert_stations_coords(stations_df):
    """
        Converts the station lat/long coordinates for mapping
    """

    stations_df['lat_era5'] = stations_df.apply(lambda x: (-1 * x['  LAT'] if x['N'] == 'S' else 1 * x['  LAT']),
                                                axis=1)
    # This works with 360-x or -1*x???
    stations_df['lon_era5'] = stations_df.apply(lambda x: (-1* x[' LONG'] if x['E'] == 'W' else 1 * x[' LONG']),
                                                axis=1)

    return stations_df


def get_analysis_folder(FAA, WMO, year):
    return config.analysis_folder + str(FAA) + " - " + str(WMO) + "/" + str(year) + "_analysis/"


def get_data_folder(FAA, WMO, year):
    return config.parent_folder + str(FAA) + " - " + str(WMO) + "/" + str(year) + "/"


def _numeric_probability_columns(df):
    """Probability-bin columns parsed from saved CSV headers, in file order."""
    values = []
    for column in df.columns:
        try:
            values.append((column, float(column)))
        except (TypeError, ValueError):
            continue
    return values


def subset_probability_columns(df, min_alt=None, max_alt=None,
                               min_pressure=None, max_pressure=None):
    """Return only the saved probability-bin columns inside the configured range.

    This operates on the columns already present in a batchAnalysis CSV, so later
    decadal scripts can tighten altitude/pressure bounds without forcing the
    expensive station-level batchAnalysis rerun. Existing bin spacing is
    preserved; only out-of-range columns are removed.
    """
    min_alt = config.min_alt if min_alt is None else min_alt
    max_alt = config.max_alt if max_alt is None else max_alt
    min_pressure = config.min_pressure if min_pressure is None else min_pressure
    max_pressure = config.max_pressure if max_pressure is None else max_pressure

    keep = []
    for column, value in _numeric_probability_columns(df):
        if config.type == "ALT" and min_alt <= value * 1000.0 <= max_alt:
            keep.append(column)
        if config.type == "PRES" and min_pressure <= value <= max_pressure:
            keep.append(column)

    return df.loc[:, keep].copy()


def probability_range_label(df=None):
    """Human-readable ALT/PRES range label for titles and logging."""
    numeric_columns = []
    if df is not None:
        numeric_columns = [value for _, value in _numeric_probability_columns(df)]

    if numeric_columns:
        low = min(numeric_columns)
        high = max(numeric_columns)
        if config.type == "ALT":
            return f"{low:.1f}-{high:.1f} km"
        return f"{low:.1f}-{high:.1f} hPa"

    if config.type == "ALT":
        return f"{config.min_alt / 1000.0:.1f}-{config.max_alt / 1000.0:.1f} km"
    return f"{config.min_pressure:.1f}-{config.max_pressure:.1f} hPa"


def _monthly_csv_path(FAA, WMO, year, month):
    """Path of the monthly wind-probabilities CSV written by save_wind_probabilties.

    Mirrors the suffix built there: ``{FAA} - {WMO}-{year}-{month}`` (month is the
    plain integer 1-12, no zero-padding).
    """
    return os.path.join(get_analysis_folder(FAA, WMO, year),
                        str(FAA) + " - " + str(WMO) + "-" + str(year) + "-" + str(month) + ".csv")


def _done_sentinel_path(FAA, WMO, year):
    """Path of the ``.done`` sentinel marking a fully-analyzed station-year."""
    return os.path.join(get_analysis_folder(FAA, WMO, year), ".done")


def missing_months(FAA, WMO, year):
    """Months (1-12) that do not yet have a written monthly CSV.

    Used by the resume logic so an interrupted station re-derives only the months
    it never finished, rather than restarting all 12.
    """
    return [m for m in range(1, 13)
            if not os.path.exists(_monthly_csv_path(FAA, WMO, year, m))]


def monthly_complete(FAA, WMO, year):
    """Whether a station-year's monthly analysis is complete.

    Complete iff the ``.done`` sentinel exists OR all 12 monthly CSVs are present.
    The 12-CSV fallback keeps pre-sentinel output (existing ``*_ANALYSIS_*`` dirs)
    from being needlessly re-analyzed; the sentinel makes new runs unambiguous.
    A half-finished folder (e.g. an interrupted / OOM-killed worker that wrote only
    some months) is therefore NOT treated as done, so the next run resumes it.
    """
    if os.path.exists(_done_sentinel_path(FAA, WMO, year)):
        return True
    return len(missing_months(FAA, WMO, year)) == 0


def mark_monthly_done(FAA, WMO, year):
    """Write the ``.done`` sentinel once all 12 months are present.

    Called after a station's full monthly set has been written so subsequent runs
    skip it via monthly_complete without re-counting CSVs.
    """
    sentinel = _done_sentinel_path(FAA, WMO, year)
    os.makedirs(os.path.dirname(sentinel), exist_ok=True)
    with open(sentinel, "w") as f:
        f.write("")


def check_analyzed(FAA, WMO, year, path, category):
    """
        Check whether a station-year's <category> output already exists.

        For the "monthly" category this is completeness-aware: the station counts
        as analyzed only if its full monthly set is complete (see monthly_complete).
        A half-finished folder is NOT treated as done, so the next run resumes it
        instead of freezing partial output. All other categories (e.g. "annual")
        fall back to plain path existence.
    """
    if category == "monthly":
        isExist = monthly_complete(FAA, WMO, year)
    else:
        isExist = os.path.exists(path)

    if not isExist:
        print(colored(str(FAA) + "-" + str(WMO) + "/" + str(
            year) + " " + category + " data not yet analyzed.", "yellow"))
        return False

    print(colored(str(FAA) + "-" + str(WMO) + "/" + str(
        year) + " " + category + " data already analyzed.", "green"))
    return True


def _atomic_write(final_path, write_fn, tmp_suffix=".tmp"):
    """Write a file via a temp file in the same directory, then os.replace into place.

    ``os.replace`` (rename(2)) is atomic on POSIX and Windows, so a crash mid-write
    can never leave a half-written file at ``final_path``: readers (the annual
    aggregation, the resume/completeness gate) always see either the complete old
    file or the complete new one. The temp lives in the same directory so the rename
    stays on one filesystem - a cross-device move would not be atomic.

    ``write_fn`` is called with the temp path and must write the full file there.
    ``tmp_suffix`` controls the temp file's extension: keep it OFF the final
    extension for CSVs (so analyze_annual_data's ``*.csv`` scan ignores a stray temp)
    but ON it for PNGs (dfi.export infers the image format from the extension).
    """
    final_path = Path(final_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(final_path.parent),
                               prefix="." + final_path.stem + ".",
                               suffix=tmp_suffix)
    os.close(fd)
    try:
        write_fn(tmp)
        os.replace(tmp, final_path)
    except BaseException:
        # Don't leave orphan temp files behind if the write or replace failed.
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def export_colored_dataframes(df, title, path, suffix, precision=2, export_color=True,
                              vmin=0.0, vmax=1.0, cmap='RdYlGn', mode=config.dfi_mode):

    """
    Exports up to 2 dataframes:
        * a .csv of the dataframe
        * if export_color is true, a colored .png of the table as well


    .. note::
        You may need to install the following if now already installed:
            * chrome driver
            * Selenium
        The default for dataframe_image is to use chrome. But this doesn't work well with WSL.
        Matplotlib is an option as well, but it doesn't allow for css customization, so no titles or captions
    
    ... 6/25/26 REVISED ::
        Chrome will crash due to an overload in keychain calls, it calls a new window PER image,
        which leads to 1000+ images over the course of a full run
        Matplotlib is an option but it runs really slow (100+ seconds per image) due to being cpu heavy,
        It generates each html format and then has to recalculate cell size as it reads the csv

        Chromium is the new default, which running under --password-store=basic and --use-mock-keychain
        flags should allow the program to no longer crash.
    """

    df.index.name = None

    df = df.apply(pd.to_numeric)

    df_styled = df.style.background_gradient(axis=None, vmin=vmin, vmax=vmax, cmap=cmap)

    if 'std' in df:
        cmaps = {'std': 'winter_r'}
        for col, cmap in cmaps.items():
            df_styled = df_styled.background_gradient(cmap, subset=col, vmin=0.0, vmax=.35)

    df_styled = df_styled.set_caption(title).set_table_styles([
        {
            'selector': 'caption',
            'props': [
                ('color', 'black'),
                ('font-weight', 'bold'),
                ('font-size', '26px'),
                ('padding-bottom', '10px')
            ]
        },
        # Cell sizing for the browser (playwright) render; 19px == the matplotlib
        # backend's 14pt, so both look alike. matplotlib ignores this CSS (no-op there).
        {
            'selector': 'td',
            'props': [
                ('min-width', '50px'),
                ('text-align', 'center'),
                ('padding', '10px 6px'),
                ('font-size', '19px')
            ]
        },
        {
            'selector': 'th',
            'props': [
                ('min-width', '50px'),
                ('text-align', 'center'),
                ('padding', '10px 6px'),
                ('font-size', '19px')
            ]
        },
        {
            'selector': 'th.row_heading',
            'props': [
                ('white-space', 'nowrap'),
                ('text-align', 'right')
            ]
        }
    ])

    df_styled = df_styled.format(precision=precision)

    if export_color:
        filepath_image = Path(path + '/' + suffix + '.png')
        # dfi infers the image format from the extension, so the temp must end in .png.
        _atomic_write(filepath_image,
                      lambda tmp: dfi.export(df_styled, tmp, max_rows=-1, max_cols=-1,
                                             table_conversion=mode),
                      tmp_suffix=".png")

    filepath_dataframe = Path(path + '/' + suffix + '.csv')
    # Temp ends in .tmp (not .csv) so a stray temp is ignored by the annual ".csv" scan.
    _atomic_write(filepath_dataframe, lambda tmp: df.to_csv(tmp))


# ============================ PARALLEL DRIVER ============================

def run_parallel_analysis(worker, tasks, num_workers=None, initializer=None, initargs=()):
    """Run ``worker`` over ``tasks`` in a bounded process pool, surfacing failures.

    Shared by all four batchAnalysis variants so the scheduling layer lives in one
    place (no more 4-way drift, dead Manager().Queue() plumbing, or unbounded
    one-process-per-station spawning).

    :param worker: top-level callable invoked as ``worker(*args)`` for each task.
                   Must be importable (picklable) for the ``spawn`` start method
                   used on macOS / Windows - no lambdas or closures.
    :param tasks:  iterable of ``(label, args)`` pairs, one per station. ``label``
                   is a human-readable station id used only for reporting; ``args``
                   is the argument tuple passed to ``worker``.
    :param num_workers: pool size. ``None`` -> ``config.num_workers`` (mode-dependent
                   default; see config.py). Capped at ``len(tasks)``.
    :param initializer / initargs: forwarded to ProcessPoolExecutor so each worker
                   process can do one-time setup (e.g. opening the forecast once per
                   process instead of once per task). No-op in radiosonde mode.
    :returns: list of ``(label, status, error)`` where status is "ok" or "failed".
    """
    tasks = list(tasks)
    if not tasks:
        print(colored("No stations to analyze.", "yellow"))
        return []

    if num_workers is None:
        num_workers = config.num_workers or (os.cpu_count() or 1)
    num_workers = max(1, min(num_workers, len(tasks)))

    print(colored(
        "Dispatching " + str(len(tasks)) + " stations across " + str(num_workers) + " workers...",
        "cyan"))

    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers,
                                                initializer=initializer,
                                                initargs=initargs) as executor:
        future_to_label = {executor.submit(worker, *args): label for label, args in tasks}
        try:
            for future in concurrent.futures.as_completed(future_to_label):
                label = future_to_label[future]
                try:
                    future.result()
                    results.append((label, "ok", None))
                except Exception as e:
                    # A worker that raised (surfaced exception) or whose process died
                    # mid-task (e.g. OOM -> BrokenProcessPool) lands here instead of
                    # silently passing as success.
                    results.append((label, "failed", repr(e)))
                    print(colored("WORKER FAILED for " + label + " -> " + repr(e), "red"))
        except KeyboardInterrupt:
            print(colored("Caught KeyboardInterrupt, cancelling pending workers", "red"))
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    failed = [r for r in results if r[1] != "ok"]
    if failed:
        print(colored(
            "\n" + str(len(failed)) + " of " + str(len(tasks)) + " stations failed:", "red"))
        for label, _status, error in failed:
            print(colored("    " + label + " -> " + str(error), "red"))
    else:
        print(colored(
            "All " + str(len(tasks)) + " stations completed successfully.", "green"))

    return results
