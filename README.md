# Observable Fast Rotators

**Author:** Juan Cabanela

This is a Python script to retrieve JPL Horizons data on quick rotating asteroids.  Specifically, it calls the JPL Horizons database and retrieves a list of all the asteroids with semi-major axis < 2.5 AU and *KNOWN* rotation periods of less than 3.5 hours.  Once that list of asteroids has been retrieved, it makes a series of queries to pyephem to determine which asteroids are visible from Feder Observatory this coming evening (airmass < 3 for at least 60 minutes).

## Requirements

- Python 2.7 (will *NOT* run in Python 3.5)
- CALLHORIZONS 1.0.1 or greater Python Library
