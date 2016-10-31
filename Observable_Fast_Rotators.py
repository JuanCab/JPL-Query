from __future__ import print_function
import numpy as np
import telnetlib
import re
import sys
import ephem

# Check to see if running Python 3, which I know presents problems.
if sys.version_info[0] == 3:
    sys.exit("\nWARNING: This script requires callhorizons which is Python 2.7 only.\n")
else:
    import callhorizons

# Test script to retrieve JPL Horizons data on quick rotating asteroids


def airmass(alt):
    """
    Given apparent altitude find airmass.
    R.H. Hardie, 1962, `Photoelectric Reductions', Chapter 8 of Astronomical
    Techniques, W.A. Hiltner (Ed), Stars and Stellar Systems, II (University
    of Chicago Press: Chicago), pp178-208.
    """
    sm1 = 1.0 / np.sin(alt) - 1.0
    return 1.0 + sm1 * (0.9981833 - sm1 * (0.002875 + 0.0008083 * sm1))

# Telnet JPL Horizons system and get the list of asteroids with rotation
# periods <3.5 hours and orbiting between 0.9 and 2.5 AU from Sun
print("")
print("* Querying JPL Horizons telnet service to retrieve list of asteroids ")
print("  with periods of <3.5 hours and orbits between 0.9 and 2.5 AU from Sun.")

jpl = telnetlib.Telnet()
jpl.open('horizons.jpl.nasa.gov', 6775)

expect = ((b'Horizons> ', b'PAGE OFF\n'),
          (b'Horizons> ', b'ROTPER<3.5, ROTPER>0.0, ADIST<2.5, QR>0.9\n'),
          (b' ] :', b'y\n'))

# The original version of this loop did NOT work with Python 3.5 because
# now a simple string is returned as byte variable instead of a UNICODE (2-byte
# per character) string.  I had to modify the expect variable above to be
# explicitly bytes so it works with both 2.7 and 3.5.
for i in expect:
    jpl.read_until(i[0])
    jpl.write(i[1])

# At this point a list of matching asteroids should appear
# Following lines had to be changed to pass their strings as a byte-like
# object for Python 3.5 to accept this code.
fast_rotators_raw = jpl.read_until(b' <cr>:')
fast_rotators_lines = fast_rotators_raw.split(b'\n')

print("* Telnet query done.  Parsing query...")


# Set up empty lists for later use
fast_rotators_recnum = []      # Record number
fast_rotators_name = []        # Name
fast_rotators_rotper = []      # Rotation Period
fast_rotators_mag = []         # maximum V magnitude (est)
fast_rotators_minairmass = []  # Minimum airmass
fast_rotators_vis = []         # Minutes of visibility
fast_rotators_ephem = []       # Ephemeris for night
fast_rotators_score = []       # Computed score

# Parse the lines
num_rot = 0
for line_bytes in fast_rotators_lines:
    line = line_bytes.decode("utf-8")   # Added for Python 3.5 compatibility
    if re.search(' +[0-9]+ +[0-9]+ +', line):
        # Hardcoded the matching columns for now
        fast_rotators_recnum.append(int(line[4:12]))
        primary = line[24:37]
        name = line[39:62]
        if re.search('.*undefine.*', primary):
            fast_rotators_name.append(name.strip())
        elif re.search('.*unnamed.*', name):
            fast_rotators_name.append(primary.strip())
        else:
            fast_rotators_name.append("%s (%s)" % (name.strip(), primary.strip()))

        fast_rotators_rotper.append(float(line[63:73]))
        num_rot += 1

# Loop through all those objects and check their status

# Set up Feder observatory parameters for pyephem computations
feder = ephem.Observer()
feder.lon = -96.45328 / 180. * np.pi
feder.lat = 46.86678 / 180. * np.pi
feder.elevation = 311  # m
feder.date = '2016/08/03 00:00'  # UT
feder.pressure = 0       # Doesn't compensate for air
feder.horizon = '-0:34'  # This is for purposes of computing sunrise/set

# Retrieve nest set and next rising times in UT
sun = ephem.Sun()
start_of_Obs = ephem.date(feder.next_setting(sun) + ephem.hour)
end_of_Obs = ephem.date(feder.next_rising(sun) - ephem.hour)
start_time = "%s" % ephem.localtime(start_of_Obs)
end_time = "%s" % ephem.localtime(end_of_Obs)
mag_lim = 17.0
airmass_lim = 3.0
minutes_visible_lim = 60.0
ephemhdr = "\n%-18s %-11s %-11s %-05s %-04s\n" % ("Date", "RA", "Dec", "mag", "secz")

print("")
print("* Checking ", num_rot, " fast rotating asteroids found on JPL horizons.")
print("  Require at least ", minutes_visible_lim, " minutes visibility at Feder")
print("  between ", start_time, " to ", end_time, " (local)")
print("  with a limiting V magnitude of ", mag_lim, ".")
print("")
print("* Objects checked (of %d): " % (num_rot), end="")

# Retrieve data on each fast rotating asteroid and convert to pyephem data for manipulation
num_found = 0  # Number of observable fast rotating asteroids found
for i in range(num_rot):
    # print("  * Checking ", fast_rotators_name[i], " (asteroid ", i + 1, " of ", num_rot, ")")
    if i % 25 == 0:
        print("%d.." % i, end="")
        sys.stdout.flush()

    # The following line FAILS in Python 3.5 with a
    # AttributeError: module 'callhorizons' has no attribute 'query'
    fast_rot_cand = callhorizons.query(fast_rotators_recnum[i])
    fast_rot_cand.set_epochrange(start_time, end_time, '1h')
    # lines = fast_rot_cand.get_ephemerides(730)  # Get info for UND obs. code
    # print('Number of lines of ephemeris retrieved: ', lines)
    fast_rot_cand_pyephem = fast_rot_cand.export2pyephem()
    aster = fast_rot_cand_pyephem[0]

    # Check visibility at Feder
    feder.date = ephem.date(start_of_Obs)
    end = ephem.date(end_of_Obs)
    minutes_visible = 0
    maxmag = 0
    minairmass = 20
    while feder.date < end:
        aster.compute(feder)
        # Only consider it observable if airmass is < 3
        secz = airmass(aster.alt)
        if (secz < airmass_lim and secz > 0):
            if aster.mag > maxmag:
                maxmag = aster.mag
            if secz < minairmass:
                minairmass = secz
            minutes_visible += 1
        feder.date += 1. / (24. * 60.)

    # Store information about visibility
    fast_rotators_mag.append(maxmag)
    fast_rotators_vis.append(minutes_visible)
    fast_rotators_minairmass.append(minairmass)

    # If we pass the magnitude and minutes visible threshold, save ephemeris
    ephemstr = ephemhdr
    if (minutes_visible >= minutes_visible_lim) and (maxmag < mag_lim):
        num_found += 1
        # print("   * ", fast_rotators_name[i], " visible ", minutes_visible, " minutes with V~", maxmag)
        feder.date = ephem.date(start_of_Obs)
        end = ephem.date(end_of_Obs)
        while feder.date < end:
            aster.compute(feder)
            # Only consider it observable if airmass is < 3
            secz = airmass(aster.alt)
            if (secz < 3 and secz > 0):
                ephemstr += "%18s %11s %11s %05.2f %04.2f\n" % (feder.date, aster.ra, aster.dec, aster.mag, secz)
            feder.date += 1. / (24. * 4.)  # Every 15 minutes
        # print(ephemstr)
        fast_rotators_ephem.append(ephemstr)

        # Assign a score to this asteroid
        #  -1* (hours visible + brightness ratio above limit - minimum airmass)
        score = (minutes_visible / 60.) + (mag_lim - maxmag) * 2.5 - minairmass
        fast_rotators_score.append(-1 * score)
    else:
        fast_rotators_ephem.append("")
        fast_rotators_score.append(100)

print("\n")

#
# Once done with review, sort list of asteroids by score and print data for
# the observable ones.
#
sorted_idx = sorted(range(len(fast_rotators_score)), key=fast_rotators_score.__getitem__)

for i in sorted_idx:
    if (fast_rotators_score[i] < 100):
        print("* Asteroid %s with rotation period %5.3f hours visible %d min" % (fast_rotators_name[i], fast_rotators_rotper[i], fast_rotators_vis[i]))
        print("  with minimum airmass %5.3f and V~%6.3f" % (fast_rotators_minairmass[i], fast_rotators_mag[i]))
        # print("  SCORE: %f" % (fast_rotators_score[i]))
        # print("  IDX: %d" % (i))
        print(fast_rotators_ephem[i], "\n")
