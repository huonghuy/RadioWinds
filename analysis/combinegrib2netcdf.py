"""
Merge monthly ERA5 GRIB files into a single yearly NetCDF using CDO.
Different from combinegrib2netcdf.py


"""

import os
import glob
import shutil
import subprocess


def merge_year(year, output_dir="era5_data", expected_months=12):
    """Combine one year's monthly GRIBs into a yearly NetCDF.

    Defensive: verifies CDO is installed, the year folder exists, the
    monthly files are present, and the output isn't already built.
    Returns the output path on success, or None if it skipped/failed.
    """
    # 0. Is CDO even on PATH?
    if shutil.which("cdo") is None:
        print("[warn] 'cdo' not found — skipping merge")
        return None

    year = str(year)                       # tolerate int years like 2023
    year_dir = os.path.join(output_dir, year)
    out_file = os.path.join(year_dir, f"era5_{year}_complete.nc")

    # 1. Does the subfolder exist at all?
    if not os.path.isdir(year_dir):
        print(f"[warn] {year_dir} doesn't exist — nothing to merge")
        return None

    # 2. Already merged? Don't redo 30 minutes of work.
    if os.path.exists(out_file):
        print(f"[skip] {out_file} already exists")
        return out_file

    # 3. Are the monthly files actually present?
    monthly = sorted(glob.glob(os.path.join(year_dir, f"era5_{year}_*.grib")))
    if not monthly:
        print(f"[warn] no monthly files in {year_dir} — skipping")
        return None
    if len(monthly) < expected_months:
        print(f"[warn] only {len(monthly)}/{expected_months} months for {year}; "
              "merging would leave a gap. Skipping.")
        return None

    # 4. Merge.
    print(f"[merge] {len(monthly)} files -> {out_file}")
    subprocess.run(["cdo", "-f", "nc", "mergetime", *monthly, out_file], check=True)
    print(f"[done ] {out_file}")
    return out_file


if __name__ == "__main__":
    import sys
    for y in sys.argv[1:]:               # e.g. python era5_merge.py 2023 2024
        merge_year(y)