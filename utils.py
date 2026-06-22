import pandas as pd
import config
import dataframe_image as dfi
from pathlib import Path
import os
import sys
from termcolor import colored
import glob

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


def check_analyzed(FAA, WMO, year, path, category):
    """
        Check if the radiosonde data has been downloaded yet
    """
    isExist = os.path.exists(path)
    if not isExist:
        print(colored(str(FAA) + "-" + str(WMO) + "/" + str(
            year) + " " + category + " data not yet analyzed.", "yellow"))
        return False

    print(colored(str(FAA) + "-" + str(WMO) + "/" + str(
        year) + " " + category + " data already analyzed.", "green"))
    return True


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
    """

    df.index.name = None

    df = df.apply(pd.to_numeric)

    df_styled = df.style.background_gradient(axis=None, vmin=vmin, vmax=vmax, cmap=cmap)

    if 'std' in df:
        cmaps = {'std': 'winter_r'}
        for col, cmap in cmaps.items():
            df_styled = df_styled.background_gradient(cmap, subset=col, vmin=0.0, vmax=.35)

    df_styled = df_styled.set_caption(
        title).set_table_styles([{
            'selector': 'caption',
            'props': [
                ('color', 'black'),
                ('font-weight', 'bold'),
                ('font-size', '20px')
            ]
        }])

    df_styled = df_styled.format(precision=precision)

    if export_color:
        filepath_image = Path(path + '/' + suffix + '.png')
        filepath_image.parent.mkdir(parents=True, exist_ok=True)
        dfi.export(df_styled, filepath_image, max_rows=-1, max_cols=-1, table_conversion=mode)

    filepath_dataframe = Path(path + '/' + suffix + '.csv')
    filepath_dataframe.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath_dataframe)