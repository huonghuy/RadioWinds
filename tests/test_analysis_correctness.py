# ruff: noqa: E402 -- repository root must be on sys.path before project imports
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import pytest
import xarray as xr

import config
from utils import sounding_datetime
from analysis.Forecast import Forecast
from analysis.checkRadiosondeDownloads import inspect_downloads
from analysis.combineNETCDF import collapse_expver
from analysis.opposing_wind_wyoming import determine_calm_winds


def load_script(relative_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("relative_path", "module_name", "suffix", "missing_name", "complete_name"),
    [
        (
            "analysis/batchAnalysis-Calm.py",
            "batch_analysis_calm_test",
            "CALM",
            "calm_missing_months",
            "calm_monthly_complete",
        ),
        (
            "analysis/batchAnalysis-Full.py",
            "batch_analysis_full_test",
            "FULL",
            "full_missing_months",
            "full_monthly_complete",
        ),
    ],
)
def test_variant_completion_ignores_total_outputs(
    tmp_path,
    monkeypatch,
    relative_path,
    module_name,
    suffix,
    missing_name,
    complete_name,
):
    module = load_script(relative_path, module_name)
    analysis_dir = tmp_path / "AAA - 12345" / "2020_analysis"
    analysis_dir.mkdir(parents=True)
    monkeypatch.setattr(
        module.utils,
        "get_analysis_folder",
        lambda FAA, WMO, year: str(analysis_dir) + "/",
    )

    for month in range(1, 13):
        (analysis_dir / f"AAA - 12345-2020-{month}.csv").touch()
    (analysis_dir / ".done").touch()

    assert getattr(module, missing_name)("AAA", 12345, 2020) == list(range(1, 13))
    assert not getattr(module, complete_name)("AAA", 12345, 2020)

    for month in range(1, 13):
        (analysis_dir / f"AAA - 12345-2020-{month}-{suffix}.csv").touch()

    assert getattr(module, complete_name)("AAA", 12345, 2020)


def test_calm_winds_honors_function_threshold(monkeypatch):
    monkeypatch.setattr(config, "type", "ALT")
    frame = pd.DataFrame(
        {
            "speed": [1.5, 3.0],
            "height": [15000.0, 16000.0],
            "pressure": [100.0, 90.0],
        }
    )

    result = determine_calm_winds(frame, speed_threshold=2.0, alt_step=500)

    assert result.tolist() == [15000.0]



def test_forecast_rejects_simulation_before_model_start(monkeypatch):
    model_start = datetime(2020, 1, 2)
    model_end = datetime(2020, 1, 3)

    def fake_load(self, _path):
        self.model_start_datetime = model_start
        self.model_end_datetime = model_end
        self.source = "unknown"
        self.resolution_deg = None

    monkeypatch.setattr(Forecast, "_load", fake_load)
    simulation = {
        "dt": 60,
        "start_time": model_start - timedelta(hours=1),
        "sim_time": 1,
        "start_coord": {"lat": 0.0, "lon": 0.0, "alt": 0.0},
    }
    monkeypatch.setattr(config, "simulation", simulation, raising=False)

    with pytest.raises(ValueError, match="precedes forecast start"):
        Forecast(simulation["start_coord"])


def test_forecast_reports_altitude_from_current_time_index():
    reader = Forecast.__new__(Forecast)
    reader.model_start_datetime = datetime(2020, 1, 1)
    reader.resolution_hr = 1.0
    reader.lat = np.array([0.0])
    reader.lon = np.array([0.0])
    reader.hgtprs = np.array([[[[100.0]]], [[[200.0]]]])
    reader.min_alt_m = 0.0
    reader.LAT_LOW = -90.0
    reader.LAT_HIGH = 90.0
    reader.LON_LOW = -180.0
    reader.LON_HIGH = 180.0
    reader.getNearestLatIdx = lambda _lat: 0
    reader.getNearestLonIdx = lambda _lon: 0
    reader.getNearestAltbyIndex = lambda *_args: 0
    reader.wind_alt_Interpolate2 = lambda *_args: [0.0, 0.0, 0.0, 0.0]

    class FakeGeodesic:
        @staticmethod
        def Direct(lat, lon, _bearing, _distance):
            return {"lat2": lat, "lon2": lon}

    reader.geod = FakeGeodesic()
    coord = {
        "lat": 0.0,
        "lon": 0.0,
        "alt": 1000.0,
        "timestamp": datetime(2020, 1, 1, 1),
    }

    result = reader.getNewCoord(coord, dt=60)

    assert result[-1] == 200.0


def test_download_layout_ignores_completion_markers(tmp_path, capsys):
    year_dir = tmp_path / "AAA - 12345" / "2020"
    year_dir.mkdir(parents=True)
    (year_dir / ".download_complete").touch()
    for month in range(1, 13):
        month_dir = year_dir / str(month)
        month_dir.mkdir()
        (month_dir / ".download_complete").touch()
        (month_dir / f"sounding-{month}.csv").touch()

    stations, soundings = inspect_downloads(tmp_path, check_total_soundings=True)

    assert stations == 1
    assert soundings == 12
    assert capsys.readouterr().out == ""


def test_collapse_expver_is_optional_and_prefers_one():
    no_expver = xr.Dataset({"u": ("x", [1.0, 2.0])})
    assert collapse_expver(no_expver) is no_expver

    dataset = xr.Dataset(
        {"u": (("expver", "x"), [[np.nan, 2.0], [5.0, 6.0]])},
        coords={"expver": [1, 5], "x": [0, 1]},
    )

    collapsed = collapse_expver(dataset)

    np.testing.assert_allclose(collapsed["u"].values, [5.0, 2.0])


def test_sounding_datetime_survives_empty_wind_filter_and_has_filename_fallback():
    frame = pd.DataFrame(
        {
            "time": ["2016-12-03", "2016-12-03"],
            "direction": [np.nan, np.nan],
            "speed": [np.nan, np.nan],
        }
    )
    filtered = frame.dropna(subset=["direction", "speed"], how="all")

    assert filtered.empty
    assert sounding_datetime(frame) == pd.Timestamp("2016-12-03")
    assert sounding_datetime(
        pd.DataFrame(), "PHTO-2016-12-3-0.csv"
    ) == pd.Timestamp("2016-12-03 00:00:00")


def test_calm_analysis_records_no_wind_sounding_as_missing(tmp_path, monkeypatch):
    module = load_script(
        "analysis/batchAnalysis-Calm.py", "batch_analysis_calm_missing"
    )
    data_dir = tmp_path / "data"
    month_dir = data_dir / "12"
    analysis_dir = tmp_path / "analysis"
    month_dir.mkdir(parents=True)
    analysis_dir.mkdir()
    pd.DataFrame(
        {
            "height": [1000.0, 2000.0],
            "pressure": [900.0, 800.0],
            "direction": [np.nan, np.nan],
            "speed": [np.nan, np.nan],
            "time": ["2016-12-03", "2016-12-03"],
        }
    ).to_csv(month_dir / "PHTO-2016-12-3-0.csv")

    exported = {}
    monkeypatch.setattr(module, "calm_monthly_complete", lambda *_args: False)
    monkeypatch.setattr(module, "calm_missing_months", lambda *_args: [12])
    monkeypatch.setattr(
        module.utils, "get_data_folder", lambda *_args: str(data_dir) + "/"
    )
    monkeypatch.setattr(
        module.utils, "get_analysis_folder", lambda *_args: str(analysis_dir) + "/"
    )
    monkeypatch.setattr(
        module.utils,
        "export_colored_dataframes",
        lambda frame, **_kwargs: exported.setdefault("frame", frame.copy()),
    )

    assert module.anaylze_monthly_data("PHTO", 91285, 2016)
    sounding = exported["frame"].loc[pd.Timestamp("2016-12-03")]
    assert sounding.isna().all()

