# -*- coding: utf-8 -*-


# MAXSPEEDS
# ALL VALUES IN KM/H

SPEED_DEFAULTS_CAR = {
    "urban": 50,
    "highway": {"living_street": 20, "trunk": 110, "motorway": 130},
    "else": 90,
}

COUNTRY_MODIFIER_CAR = {
    "at": {"else": 100, "trunk": 100},
    "be": {"motorway": 120, "rural": 70, "urban": 30},
    "by": {"urban": 60, "motorway": 110},
    "ch": {"else": 80, "trunk": 110, "motorway": 120},
    "de": {"living_street": 7, "else": 100},
    "dk": {"else": 80},
    "fr": {"else": 80},
    "gb": {"motorway": (70 * 1609) / 1000},
    "nl": {"else": 80, "trunk": 100},
    "no": {"else": 80, "motorway": 110},
    "pl": {"else": 100, "trunk": 120, "motorway": 140},
    "ro": {"trunk": 100},
    "ru": {"else": 60, "motorway": 110},
    "uk": {"motorway": (70 * 1609) / 1000},
    "za": {"urban": 60, "else": 100},
}


# SPEED CONFIGURATION BY MODE

# replace_maxspeed : boolean, if not None, replace maxspeed
# else use default if maxspeed is empty
# max = if not None, limit maxspeed below max


WALK_SPEED = {"mode": "walk", "replace_maxspeed": 4.0, "max": None}
BIKE_SPEED = {"mode": "bike", "replace_maxspeed": 16.0, "max": None}

RAIL_SPEED = {"mode": "rail", "replace_maxspeed": None, "default": 50.0, "max": None}
TRANSIT_SPEED = {
    "mode": "transit",
    "replace_maxspeed": None,
    "default": 50.0,
    "max": 80.0,
}

DRIVE_SPEED = {
    "mode": "drive",
    "replace_maxspeed": None,
    "default": 50.0,
    "max": None,
}