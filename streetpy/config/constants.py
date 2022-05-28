# -*- coding: utf-8 -*-

# suffix for reverse column
REV_SUFFIX = "_r"

# max speed column name
SPEED = "maxspeed"

# urban column
URBAN = "urban"

# highway and railway types column
HIGHWAY = "highway"
RAILWAY = "railway"

# junction column
JUNCTION = "junction"

# forward travel time column, reverse as TIME + REV_SUFFIX
TIME = "time"

# conversion constants
UNIT_CONV = {"MPH": 1.60934, "mph": 1.60934}


# modal configuration, keys are modal keys
# mode : name used for columns or mode filtering
# bidi : boolean, if True, all edges are bidirectionnal, e.g. walk

MODES = {
    "WALK": {"mode": "walk", "bidi": True, "hierarchy": HIGHWAY},
    "BIKE": {"mode": "bike", "bidi": False, "hierarchy": HIGHWAY},
    "TRANSIT": {"mode": "transit", "bidi": False, "hierarchy": HIGHWAY},
    "DRIVE": {"mode": "drive", "bidi": False, "hierarchy": HIGHWAY},
    "RAIL": {"mode": "rail", "bidi": False, "hierarchy": RAILWAY},
}

def streetpy_base_columns():
    return [SPEED, HIGHWAY]


def streetpy_optional_columns(streets=None):
    cols = [URBAN, JUNCTION]
    if streets is None:
        return cols
    else:
        return [c for c in cols if c in streets.columns]


def mode_columns(mode=None):
    """
    return modal columns
    if mode is a mode name returns a tuple of mode column, reverse column
    else return all mode columns
    """

    m = [v["mode"] for k, v in MODES.items()]
    m.extend([v["mode"] + REV_SUFFIX for k, v in MODES.items() if not v["bidi"]])
    if mode is None:
        return m

    m = [n for n in m if n == mode or n == mode + REV_SUFFIX]
    if len(m)==1:
        return m[0], None
    else:
        return m[0], m[1]


def mode_list():
    """return all possible mode names"""
    return [v["mode"] for k, v in MODES.items()]


def is_mode_bidirectional(mode):
    """returns if mode is bidirectional"""
    if mode.upper() not in MODES:
        raise ValueError("{0} not a valid mode".format(mode))
    return MODES[mode.upper()]["bidi"]


def mode_hierarchy(mode):
    """returns the mode hierarchy column name e.g. highway or railway"""
    if mode.upper() not in MODES:
        raise ValueError("{0} not a valid mode".format(mode))
    return MODES[mode.upper()]["hierarchy"]