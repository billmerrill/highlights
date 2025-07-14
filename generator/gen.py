from collections import namedtuple, defaultdict
import dataclasses
import datetime
from dataclasses import dataclass
from typing import Optional, Tuple
import os
from pprint import pprint
import re
import xml.etree.ElementTree as ET

import magic
import gpxpy
import geojson
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
        return f"Artifact(name={self.informal_name} type={self.artifact_type}, geo_bounds={self.geo_bounds}, time_bounds={self.time_bounds}, geo_bounds={self.geo_bounds})"

    @staticmethod
    def time_str(unix_timestamp):
        return datetime.datetime.fromtimestamp(unix_timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    @property
    def date(self):
        return datetime.date.fromtimestamp(self.time_bounds[0]).isoformat()

    @property
    def timestamp(self):
        return self.time_bounds[0] if self.time_bounds else None

    @property
    def informal_name(self):
        if self.artifact_type == GPX:
            return os.path.basename(self.filepath)
        elif self.artifact_type in (IMAGE, VIDEO):
            return os.path.basename(self.filepath)
        else:
            return f"Artifact({self.artifact_type}) - {os.path.basename(self.filepath)}"

@dataclass
class Day:
    _: dataclasses.KW_ONLY
    date: str
    artifacts: list[Artifact] = dataclasses.field(default_factory=list)

    def sort(self):
        self.artifacts.sort(key=lambda x: x.timestamp if x.timestamp else 0)

    # implement an interator for the day
    def __iter__(self):
        for artifact in sorted(self.artifacts, key=lambda x: x.timestamp if x.timestamp else 0):
            yield artifact  



@dataclass
class Travelogue:
    _: dataclasses.KW_ONLY
    data: dict[str, "Day"] = dataclasses.field(default_factory=dict)
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None

    def insert_artifact(self, artifact: Artifact):
        date = artifact.date
        if date not in self.data:
            self.data[date] = Day(date=date, artifacts=[])
        self.data[date].artifacts.append(artifact)

        # Update start and end dates
        if not self.start_date or artifact.timestamp < self.start_date.timestamp():
            self.start_date = datetime.datetime.fromtimestamp(artifact.timestamp)
        if not self.end_date or artifact.timestamp > self.end_date.timestamp():
            self.end_date = datetime.datetime.fromtimestamp(artifact.timestamp)

    def summarize(self):
        summary = {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "days": {},
        }
        for date, day in self.data.items():
            summary["days"][date] = {
                "artifacts_count": len(day.artifacts),
                "artifacts": [
                    f"{datetime.datetime.fromtimestamp(artifact.timestamp).isoformat()}: {artifact}"
                    for artifact in day.artifacts
                ],
            }
        return summary

    ### implement a day based iterated for the travelogue
    def __iter__(self):
        for date in sorted(self.data.keys()):
            yield self.data[date]   


def get_files(abs_root_dir):
    with os.scandir(abs_root_dir) as entries:
        files = [entry for entry in entries]
        for dir in files:
            if dir.is_dir():
                files.extend(get_files(os.path.join(abs_root_dir, dir.name)))
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
        timestamp = int(datetime.datetime.fromisoformat(timestamp_str).timestamp())

    return timestamp, lat, lon


def get_artifacts(src_files):
    artifacts = []
    for file in src_files:
        if file.is_file():
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
                timestamp, latitude, longitude = get_video_metadata(file_info.file_path)
                artifact = Artifact(
                    artifact_type=VIDEO,
                    filepath=file_info.file_path,
                    artifact_size=file_info.file_size,
                    time_bounds=(timestamp, timestamp),
                    geo_bounds=((latitude, longitude), (latitude, longitude)),
                )
                artifacts.append(artifact)
            else:
                print(
                    f"Unsupported file type: {file_info.mime_type} for {file_info.file_path}"
                )

    return artifacts


#
# Travelogue[]







def bulk_load_artifacts(travelogue, artifacts):
    for artifact in artifacts:
        if artifact.date not in travelogue.data:
            travelogue.data[artifact.date] = Day(date=artifact.date)
            travelogue.data[artifact.date].artifacts = []
        travelogue.data[artifact.date].artifacts.append(artifact)

    for day in travelogue.data:
        travelogue.data[day].sort()

    return travelogue

def gpx_to_geojson_features(gpx_file_path):
    """ Conver Tracks to LineString features, ignore waypoints for now. """
    with open(gpx_file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    features = []
    
    for track in gpx.tracks:
        for segment in track.segments:
            coordinates = []
            for point in segment.points:
                coordinates.append([point.longitude, point.latitude])

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "name": track.name,
                    "type": "track"
                }
            }
            features.append(feature)
    
    return features

def main():
    abs_home_dir = "/Users/bill/code/highlights/example-data/gpses"
    abs_home_dir = "/Users/bill/code/highlights/example-data/kootskoot"
    abs_home_dir = "/Users/bill/code/highlights/example-data/aday/Jun 17"
    output_dir = "/Users/bill/code/highlights/generator/output"
    src_files = get_files(abs_home_dir)
    artifacts = get_artifacts(src_files)
    artifacts.sort(key=lambda x: x.timestamp if x.timestamp else 0)

    travelogue = Travelogue()
    travelogue = bulk_load_artifacts(travelogue, artifacts)
    print(travelogue.summarize())

    return
    features_by_day = defaultdict(list)
    for day in travelogue:
        print(f"Day: {day.date}")
        features_by_day[day.date] = []
        for artifact in day:
            # if gpx file, convert to geojson features

            if artifact.artifact_type == GPX:
                features = gpx_to_geojson_features(artifact.filepath)
                features_by_day[day.date].extend(features)  
                print(f"  {artifact.filepath} - {len(features)} features")

            if artifact.artifact_type in (IMAGE, VIDEO):
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": artifact.geo_bounds[0]
                    },
                    "properties": {
                        "filepath": artifact.filepath,
                        "type": artifact.artifact_type,
                        "timestamp": artifact.timestamp,
                    }
                }
                features_by_day[day.date].append(feature)
                print(f"  {artifact.filepath} - {artifact.artifact_type}")

    feature_collections = []
    for date, features in features_by_day.items():
        feature_collection = geojson.FeatureCollection(features)
        with open(os.path.join(output_dir, f"koot-{date}.geojson"), "w") as fh:
            geojson.dump(feature_collection, fh)
            print(f"Saved {len(features)} features for {date} to {output_dir}/{date}.geojson")

if __name__ == "__main__":
    main()
