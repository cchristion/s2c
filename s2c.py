#!/usr/bin/env -S uv run --script

# /// script
# requires-python = "~=3.12"
# dependencies = [
#     "sqlglot[rs]==26.33",
#     "numpy<=2.2",
#     "pandas~=2.2.3",
#     "tqdm==4.67",
# ]
# ///

import argparse
import logging
from collections.abc import Generator
from pathlib import Path

import pandas as pd
import sqlglot
from tqdm import tqdm

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s : %(levelname)s : %(message)s",
    datefmt="%Y%m%dT%H%M%S",
    encoding="utf-8",
    level=logging.DEBUG,
)


def cli() -> dict:
    """CLI parser."""
    logger.debug("Parsing cli arguments.")
    parser = argparse.ArgumentParser(
        description="s2c: Script to convert all tables in a sql file to csv's.",
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Input sql file",
    )
    parser.add_argument(
        "-o",
        "--out_dir",
        type=Path,
        help='Directory to save all csv\'s default: "<file>.s2c"',
        default=Path("s2c.out"),
    )
    args = vars(parser.parse_args())

    if args["out_dir"] == Path("s2c.out"):
        args["out_dir"] = Path(args["file"].stem + ".s2c")

    logger.debug("Parsed %r arguments.", args)

    if args["out_dir"].exists():
        logger.info("Deleating %r directory", str(args["out_dir"]))

    logger.info("Creating %r directory", str(args["out_dir"]))
    args["out_dir"].mkdir(parents=True, exist_ok=True)

    return args


def file_manage(file: Path) -> Generator[str]:
    """Give chunks of sql file."""
    sql_command = ""

    with Path.open(file) as f:
        num_lines = sum(1 for _ in f)

    with Path.open(file) as f:
        for line in tqdm(f, total=num_lines):
            sql_command += line
            if line.strip().endswith(";"):
                yield sql_command
                sql_command = ""
        yield sql_command


def s2c(args: dict):
    for seg in file_manage(args["file"]):
        if "@" not in seg:
            continue
        if "INSERT" not in seg:
            continue

        lp = sqlglot.parse(seg, read="mysql")
        tbl_name = lp[0].this.this.name
        col_name = [i.name for i in lp[0].this.expressions]
        table_data = []
        for a in lp:
            if a.expression:
                for b in a.expression.expressions:
                    table_data.append(
                        [c.name for c in b.expressions],
                    )

        if not col_name:
            col_name = ["unnamed_" + str(i) for i in range(len(table_data[0]))]

        pd.DataFrame(table_data, columns=col_name).to_csv(
            f"{args['out_dir']}/{tbl_name}",
            index=False,
            na_rep="",
            mode="a",
            header=not Path(f"out/{tbl_name}").exists(),
        )


if __name__ == "__main__":
    s2c(cli())
