import argparse
import logging
import pathlib
import os
from typing import Sequence

import hrv.activity
import hrv.data
import app.model


logger = logging.getLogger(__name__)


def init_db(args) -> None:
    del args
    engine = app.model.make_engine()
    app.model.create(engine)


def cmd_import_activities(args) -> None:
    import_activities(args.files)


def import_activities(paths: Sequence[os.PathLike]) -> None:
    logger.debug(f"importing {len(paths)} activities")
    for path in paths:
        import_activity(path)


def import_activity(path: os.PathLike) -> None:
    path = pathlib.Path(path)
    logger.debug(f"importing {path}")

    if app.model.has_activity(path):
        logger.debug("activity already imported")
        return

    activity_data, recordings_data = hrv.data.load(path)
    activity_data["file_hash"] = app.model.hash_file(path)
    summary_data = hrv.activity.summarize(recordings_data)

    _ = app.model.make_engine()
    session = app.model.make_session()

    activity = app.model.Activity(**activity_data)
    session.add(activity)

    summary = app.model.Summary(**summary_data, activity=activity)
    session.add(summary)

    recordings = [
        app.model.Recording(
            activity=activity,
            name=name,
            array=data,
        )
        for name, data in recordings_data.items()
    ]
    for recording in recordings:
        session.add(recording)

    session.commit()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=pathlib.Path, default="activities.db")
    parser.add_argument("--logging", choices=["info", "debug", "warning"],
                        default="info")

    subparsers = parser.add_subparsers()

    parser_init = subparsers.add_parser("init")
    parser_init.set_defaults(func=init_db)

    parser_import = subparsers.add_parser("import")
    parser_import.set_defaults(func=cmd_import_activities)
    parser_import.add_argument("files",
                               nargs="+",
                               type=pathlib.Path,
                               help="FIT activity file(s).")

    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(level=getattr(logging, args.logging.upper()))

    args.func(args)


if __name__ == "__main__":
    main()
