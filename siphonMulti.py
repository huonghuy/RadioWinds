"""Download a month of Wyoming soundings with Siphon 0.11."""

import calendar
from datetime import datetime, timezone
import re
import time
import warnings

from requests.exceptions import HTTPError, RequestException
from siphon.simplewebservice.wyoming import WyomingUpperAir


class SiphonMulti(WyomingUpperAir):
    """Keep the original monthly interface over Siphon's timestamp API."""

    class DownloadError(RuntimeError):
        """A sounding request failed after bounded retries."""

    @classmethod
    def request_data(cls, year, month, site_id, **kwargs):
        """Return available 00/06/12/18 UTC soundings for a calendar month."""
        hours = kwargs.pop("hours", (0, 6, 12, 18))
        retries = kwargs.pop("retries", 3)
        retry_delay = kwargs.pop("retry_delay", 1.0)
        as_of = kwargs.pop("as_of", None)
        if as_of is None:
            as_of = datetime.now(timezone.utc).replace(tzinfo=None)
        if retries < 1:
            raise ValueError("retries must be at least 1")
        soundings = {}

        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            for hour in hours:
                nominal_time = datetime(year, month, day, hour)
                # Do not ask Wyoming for synoptic cycles that have not occurred yet.
                # This matters when AnnualWyomingDownload is run for the current year.
                if nominal_time > as_of:
                    continue
                df = cls._request_sounding(
                    nominal_time, str(site_id), retries, retry_delay, **kwargs
                )
                if df is None:
                    continue

                # Siphon 0.11 returns winds in m/s; RadioWinds radiosonde
                # thresholds and existing CSV files use knots.
                units = dict(getattr(df, "units", {}))
                if units.get("speed") == "m/s":
                    df[["speed", "u_wind", "v_wind"]] *= 1.9438444924406
                    units.update(speed="knot", u_wind="knot", v_wind="knot")
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        df.units = units

                # Siphon returns the actual balloon release time (commonly 11Z/23Z)
                # even though the requested observation belongs to the 12Z/00Z
                # synoptic cycle. Preserve both: RadioWinds uses nominal time for
                # filenames/analysis and release_time retains the service timestamp.
                release_time = df["time"].iloc[0]
                df["release_time"] = release_time
                df["time"] = nominal_time
                units["release_time"] = None
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    df.units = units

                # Key by release time so duplicate service responses are kept once.
                soundings.setdefault(release_time, df)

        return [soundings[key] for key in sorted(soundings)]

    @classmethod
    def _request_sounding(cls, nominal_time, site_id, retries, retry_delay, **kwargs):
        """Request one sounding, retrying only transient failures."""
        delay = retry_delay
        for attempt in range(1, retries + 1):
            try:
                return super().request_data(nominal_time, site_id, **kwargs)
            except (ValueError, RequestException) as exc:
                status = cls._http_status(exc)
                if cls._is_missing_sounding(exc, status):
                    return None

                transient = status is None or status == 429 or status >= 500
                if not transient or attempt == retries:
                    raise cls.DownloadError(
                        f"Failed station {site_id} at {nominal_time:%Y-%m-%d %HZ} "
                        f"after {attempt} attempt(s)"
                    ) from exc

                if delay > 0:
                    time.sleep(delay)
                delay *= 2

    @staticmethod
    def _http_status(exc):
        """Extract a status from Siphon's ``ValueError from HTTPError`` chain.

        Siphon's HTTP helper creates ``HTTPError`` without attaching its response,
        so the status often needs to be parsed from ``Server Error ( 404: ... )``.
        """
        current = exc
        while current is not None:
            if isinstance(current, HTTPError) and current.response is not None:
                return current.response.status_code
            match = re.search(r"Server Error \(\s*(\d{3}):", str(current))
            if match:
                return int(match.group(1))
            current = current.__cause__
        return None

    @staticmethod
    def _is_missing_sounding(exc, status):
        """Recognize Wyoming's 400/404 response for a valid but absent launch."""
        current = exc
        while current is not None:
            if (status in (400, 404)
                    and "Unable to retrieve the data" in str(current)):
                return True
            current = current.__cause__
        return False


if __name__ == "__main__":
    station = '71816'
    year = 2017
    month = 4
    df_list = SiphonMulti.request_data(year, month, station)
    print(df_list)
