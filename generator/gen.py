from collections import namedtuple
import dataclasses
import datetime
from dataclasses import dataclass
from typing import Optional, Tuple
import os
import re
import xml.etree.ElementTree as ET

import magic
import gpxpy
import exifread
from pymediainfo import MediaInfo


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


def get_exif_data(image_path):
    with open(image_path, "rb") as f:
        tags = exifread.process_file(f)

    timestamp, latitude, longitude = None, None, None

    # Check if GPS info exists
    if "GPS GPSLatitude" in tags or "GPS GPSLongitude" in tags:
        lat = tags["GPS GPSLatitude"].values
        lat_ref = tags["GPS GPSLatitudeRef"].values
        lon = tags["GPS GPSLongitude"].values
        lon_ref = tags["GPS GPSLongitudeRef"].values

        # Convert to decimal degrees
        def dms_to_decimal(dms, ref):
            degrees = float(dms[0])
            minutes = float(dms[1])
            seconds = float(dms[2])
            decimal = degrees + minutes / 60 + seconds / 3600
            if ref in ["S", "W"]:
                decimal = -decimal
            return decimal

        latitude = dms_to_decimal(lat, lat_ref)
        longitude = dms_to_decimal(lon, lon_ref)

    if "Image DateTime" in tags:
        timestamp = tags["Image DateTime"].values
        timestamp = int(
            datetime.datetime.strptime(timestamp, "%Y:%m:%d %H:%M:%S").timestamp()
        )

    return timestamp, latitude, longitude


def get_video_metadata(abs_video_path):
    # currently written to use iphone video metadata
    lat, lon = None, None
    timestamp = None

    media_info = MediaInfo.parse(abs_video_path)
    general_track = media_info.general_tracks[0]

    # example format: +49.9884-117.3743+000.000/
    if general_track.comapplequicktimelocationiso6709:
        loc = general_track.comapplequicktimelocationiso6709.rstrip("/")
        pattern = r"([+-]\d+\.\d+)([+-]\d+\.\d+)(?:([+-]\d+\.\d+))?"
        match = re.match(pattern, loc)
        lat = float(match.group(1))
        lon = float(match.group(2))

    # example format:2025-06-17T08:45:03-07:00
    if general_track.comapplequicktimecreationdate:
        timestamp_str = general_track.comapplequicktimecreationdate
        timestamp = datetime.datetime.fromisoformat(timestamp_str).timestamp()

    geo_bounds = ((lat, lon), (lat, lon))
    return timestamp, geo_bounds


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

            if mime_type == "text/xml" or mime_type == "application/gpx+xml":
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

            elif mime_type.startswith("image/"):
                # Extract EXIF data for geo point if available

                timestamp, latitude, longitude = get_exif_data(file_info.file_path)

                artifact = Artifact(
                    artifact_type=IMAGE,
                    filepath=file_info.file_path,
                    artifact_size=file_info.file_size,
                    time_bounds=(timestamp, timestamp),
                    geo_bounds=((latitude, longitude), (latitude, longitude)),
                )
                artifacts.append(artifact)

            elif mime_type.startswith("video/"):
                timestamp, geo_bounds = get_video_metadata(file_info.file_path)
                artifact = Artifact(
                    artifact_type=VIDEO,
                    filepath=file_info.file_path,
                    artifact_size=file_info.file_size,
                    time_bounds=(timestamp, timestamp),
                    geo_bounds=geo_bounds,
                )
                artifacts.append(artifact)
            else:
                print(
                    f"Unsupported file type: {file_info.mime_type} for {file_info.file_path}"
                )

    return artifacts


def main():
    abs_home_dir = "/Users/bill/code/highlights/example-data/kootskoot"
    abs_home_dir = "/Users/bill/code/highlights/example-data/gpses"
    abs_home_dir = "/Users/bill/code/highlights/example-data/aday/Jun 17"
    src_files = get_files(abs_home_dir)
    artifacts = get_artifacts(src_files)
    print(src_files)
    print(artifacts)


if __name__ == "__main__":
    main()
