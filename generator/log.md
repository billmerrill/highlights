
Jun 30, 2025 at 1:38:03 PM
First milestone generator

- This will be a cli tool that accepts a directory full of artifacts and generates
    - a catalog of artifacts arranged by day
    - clustered by location
    - a geojson (or similar) document organizing and displaying the artifacts

Later Milestone ideas: do no do
- generate an attractive path that shows the progression on a map when traces are not available
- reduction of existing traces to thumbnail the event


Jul 1, 2025 at 10:48:56 AM
Progress
- Reading the file structure
- gathering metadata for gpx and image

Next up
- reading video metadata (this looks like it'll be a long term pita)
- assemble artifact calendar
- generate geojson

Jul 12, 2025 at 4:41:49 PM
Progress
- Now reading metadate for iphone videos
- decisions.md to track data structure, naming, and style decisions.
- The travelogue now populates with all artifacts in chronological order

Next up
- generate geojson for gpx files
    - generate a list of line features per day
- generate geojson for media files
    - generate a set of point features, per day, for media

Later ideas - not for today
- limit or group media files, but not yet.
    - ideas might be related to text, when writing about media, include it on the ma
    - or manually star certain media
    - grouping to be related to camps or end of days.
- time to organize soon.
    - extractors - readers
    - translators
    - loaders - builders
