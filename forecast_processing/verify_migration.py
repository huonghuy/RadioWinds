"""verify_migration: check that forecast files in the target paths are all in
the v2 canonical schema.

Run after `migrate_v1` to confirm no v1-format files remain. Walks the same
targets (files or non-recursive directories), inspects each `.nc` with the
same `detect_format` the migrator uses, and reports:

  - v2          : in canonical layout
  - v1_gfs      : still in legacy GFS layout (NOT migrated)
  - v1_era5     : still in legacy ERA5 layout (NOT migrated)
  - era5_plev   : still in legacy ERA5 time/plev/lat/lon layout (NOT migrated)
  - unknown     : structurally unrecognized
  - backup      : `.v1.nc` backups (informational, skipped)
  - incomplete  : `.v2.tmp.nc` leftover from an aborted migration (rerun migrate_v1)

Exit code is non-zero if any file is v1/era5_plev/unknown or if any
`.v2.tmp.nc` leftover is found.

CLI:
    python -m forecast_processing.verify_migration <file_or_dir> [...]
    python -m forecast_processing.verify_migration --verbose <target>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tqdm import tqdm

from .migrate_v1 import (
    FORMAT_ERA5_PLEV,
    FORMAT_V1_ERA5,
    FORMAT_V1_GFS,
    FORMAT_V2,
    FORMAT_UNKNOWN,
    _iter_targets,
    detect_format,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m forecast_processing.verify_migration",
        description=(
            "Verify that forecast files in the target paths are all in the "
            "v2 canonical schema. Exit code 1 if any v1 or unknown files "
            "remain."
        ),
    )
    parser.add_argument(
        "targets", nargs="+", type=Path,
        help="One or more .nc files, or directories containing .nc files "
             "(non-recursive).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print one line per file. Default mode prints only non-v2 "
             "findings plus an end-of-run summary.",
    )
    args = parser.parse_args(argv)

    targets = list(_iter_targets(args.targets))
    counts = {
        FORMAT_V2: 0,
        FORMAT_V1_GFS: 0,
        FORMAT_V1_ERA5: 0,
        FORMAT_ERA5_PLEV: 0,
        FORMAT_UNKNOWN: 0,
    }
    skipped_backups: list[Path] = []
    stale_tmps: list[Path] = []
    inspect_errors: list[tuple[Path, str]] = []
    non_v2: list[tuple[Path, str]] = []

    bar = tqdm(targets, unit="file", disable=args.verbose, leave=True)
    for tgt in bar:
        bar.set_postfix_str(tgt.name[:50], refresh=False)
        if tgt.name.endswith(".v1.nc"):
            skipped_backups.append(tgt)
            if args.verbose:
                print(f"backup {tgt}")
            continue
        # A `.v2.tmp.nc` can only be debris from an aborted migrate_v1 run (a
        # successful run renames it to <name>.nc). Its presence means that
        # file's migration never finished, so flag it for attention rather
        # than inspecting it as a real forecast.
        if tgt.name.endswith(".v2.tmp.nc"):
            stale_tmps.append(tgt)
            line = (
                f"incomplete {tgt}: leftover .v2.tmp.nc from an aborted "
                "migration; rerun migrate_v1 on this file"
            )
            if args.verbose:
                print(line)
            else:
                bar.write(line)
            continue
        try:
            fmt = detect_format(tgt)
        except Exception as e:
            inspect_errors.append((tgt, str(e)))
            line = f"ERROR {tgt}: cannot inspect ({e})"
            if args.verbose:
                print(line)
            else:
                bar.write(line)
            continue
        counts[fmt] = counts.get(fmt, 0) + 1
        if fmt != FORMAT_V2:
            non_v2.append((tgt, fmt))
            line = f"{fmt} {tgt}"
            if args.verbose:
                print(line)
            else:
                bar.write(line)
        elif args.verbose:
            print(f"{FORMAT_V2} {tgt}")
    bar.close()

    print(
        f"\nVerification summary: "
        f"{counts[FORMAT_V2]} v2, "
        f"{counts[FORMAT_V1_GFS]} v1_gfs, "
        f"{counts[FORMAT_V1_ERA5]} v1_era5, "
        f"{counts[FORMAT_ERA5_PLEV]} era5_plev, "
        f"{counts[FORMAT_UNKNOWN]} unknown, "
        f"{len(inspect_errors)} inspect-errors, "
        f"{len(stale_tmps)} incomplete (.v2.tmp.nc), "
        f"{len(skipped_backups)} .v1.nc backups"
    )

    if non_v2 or inspect_errors or stale_tmps:
        print(
            f"\nFAIL: {len(non_v2) + len(inspect_errors) + len(stale_tmps)} "
            "file(s) need attention. Re-run migrate_v1 on the listed paths."
        )
        return 1
    print("OK: all inspected forecast files are v2 canonical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
