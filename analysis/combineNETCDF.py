"""Combine compatible NetCDF files by coordinates.

Inputs and output are explicit command-line arguments. Datasets without an
expver coordinate are supported; when it is present, all expver slices are
collapsed in priority order with expver=1 preferred.
"""

import argparse
from pathlib import Path

import xarray as xr
from dask.diagnostics import ProgressBar


def collapse_expver(dataset):
    """Collapse an optional expver dimension, preferring expver=1."""
    if "expver" not in dataset.dims and "expver" not in dataset.coords:
        return dataset

    values = list(dataset["expver"].values)
    values.sort(key=lambda value: (value != 1, value))
    collapsed = dataset.sel(expver=values[0], drop=True)
    for value in values[1:]:
        collapsed = collapsed.combine_first(
            dataset.sel(expver=value, drop=True)
        )
    return collapsed


def combine_netcdf(input_files, output_file, chunk_dim="time", chunk_size=10):
    """Combine input files and write one NetCDF, closing all datasets afterward."""
    datasets = []
    combined = None
    try:
        for input_file in input_files:
            dataset = xr.open_dataset(input_file, engine="netcdf4")
            if chunk_dim in dataset.dims:
                dataset = dataset.chunk({chunk_dim: chunk_size})
            datasets.append(dataset)

        combined = xr.combine_by_coords(
            datasets,
            combine_attrs="drop_conflicts",
        )
        combined = collapse_expver(combined)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_job = combined.to_netcdf(
            output_path,
            compute=False,
            engine="netcdf4",
        )
        with ProgressBar():
            print(f"Writing {output_path}")
            write_job.compute()
    finally:
        if combined is not None:
            combined.close()
        for dataset in datasets:
            dataset.close()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="Compatible input NetCDF files")
    parser.add_argument("-o", "--output", required=True, help="Output NetCDF file")
    parser.add_argument("--chunk-dim", default="time")
    parser.add_argument("--chunk-size", type=int, default=10)
    return parser.parse_args()


def main():
    args = parse_args()
    combine_netcdf(
        args.inputs,
        args.output,
        chunk_dim=args.chunk_dim,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
