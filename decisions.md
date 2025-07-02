# Decisions


## Objects

- Trip - the full recorded event
- Artifacts - any single generated file
- Camp - the place where you sleep, always associated with the end of a day, it's the destination
- Travelogue - the data structure mapping Days and Artifacts
- Days - as expected, indexed by ISO-8601 text 2025-07-01


## relations
- Camps are associated with the Day they are reached, and multiple days for layovers.
- Artifacts are ordered in Days in the Travelogue.  The user may reorder or move Artifacts within or across Days

## UX
- 