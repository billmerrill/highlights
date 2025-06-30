from collections import namedtuple
import dataclasses
import datetime
from dataclasses import dataclass
from typing import Optional, Tuple
import os
import xml.etree.ElementTree as ET

import magic
import gpxpy


FileInfo = namedtuple("FileInfo", ["file_path", "mime_type", "file_size"])


# ENUMS
GPX = "gpx"
IMAGE = "image"
VIDEO = "video"


@dataclass
class Artifact:
    _: dataclasses.KW_ONLY
    artifact_type: Optional[str] = None
    artifact_size: Optional[int] = None
    filepath: str
    geo_point: Optional[Tuple[float, float]] = None  # (latitude, longitude)
    geo_bounds: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = (
        None  # ((lat_min, lon_min), (lat_max, lon_max))
    )
    time_bounds: Optional[Tuple[int, int]] = None  # (time_start, time_end)

    def __repr__(self):
        return f"Artifact(type={self.time_str(self.time_bounds[0])}, geo_bounds={self.geo_bounds}, time_bounds={self.time_bounds})\n"

    @staticmethod
    def time_str(unix_timestamp):
        return datetime.datetime.fromtimestamp(unix_timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )


def get_files(abs_root_dir):
    with os.scandir(abs_root_dir) as entries:
        files = [entry for entry in entries]
    return files


def is_gpx(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Check if root element is 'gpx'
        if root.tag.endswith("gpx"):
            return True

        # Handle namespaced elements
        if "}gpx" in root.tag:
            return True

        return False

    except (ET.ParseError, FileNotFoundError, PermissionError):
        return False


# def parse_gpx(file_path):
#     gpx = gpxpy.parse(file_path)
#     time_bounds = gpx.get_time_bounds()
#     return {'time_point': time_bounds.start_time,
#             'start_time': time_bounds.start_time,
#             'end_time': time_bounds.end_time}


# def get_event_data(dir_entries):
#     event_stream = []

#     for entry in dir_entries:
#         ev = {'file_metadata': entry}
#         if dir_entry.mime_type == 'text/xml':
#             if is_gpx(entry['file_path']):
#                 ev['type'] = GPX
#                 ev[''] = parse_gpx(entry.file_path)


def summarize_gpx(file_path):
    """
    Preference order:
        Tracks
        Routes
        Waypoints
    """
    # Extract time bounds
    time_start = None
    time_end = None
    geo_start = (None, None)
    geo_end = (None, None)

    gpx = gpxpy.parse(open(file_path))
    time_bounds = gpx.get_time_bounds()
    if time_bounds:
        time_start = (
            int(time_bounds.start_time.timestamp()) if time_bounds.start_time else None
        )
        time_end = (
            int(time_bounds.end_time.timestamp()) if time_bounds.end_time else None
        )

    if gpx.tracks:
        # Use the first track for geo bounds
        track = gpx.tracks[0]
        if track.segments:
            segment = track.segments[0]
            if segment.points:
                geo_start = segment.points[0].latitude, segment.points[0].longitude

            omega = gpx.tracks[-1].segments[-1].points[-1]
            geo_end = omega.latitude, omega.longitude

    return time_start, time_end, geo_start, geo_end


def get_artifacts(src_files):
    artifacts = []
    for file in src_files:
        if file.is_file():
            print(file.path)
            mime_type = magic.Magic(mime=True).from_file(file.path)
            file_size = file.stat().st_size
            file_info = FileInfo(
                file_path=file.path, mime_type=mime_type, file_size=file_size
            )

            if is_gpx(file.path):
                time_start, time_end, geo_start, geo_end = summarize_gpx(
                    file_info.file_path
                )
                artifact = Artifact(
                    artifact_type=GPX,
                    filepath=file_info.file_path,
                    time_bounds=(time_start, time_end),
                    geo_bounds=(geo_start, geo_end),
                )
                artifacts.append(artifact)

    return artifacts


def main():
    abs_home_dir = "/Users/bill/code/highlights/example-data/kootskoot"
    abs_home_dir = "/Users/bill/code/highlights/example-data/gpses"
    src_files = get_files(abs_home_dir)
    artifacts = get_artifacts(src_files)
    print(src_files)
    print(artifacts)


if __name__ == "__main__":
    main()
