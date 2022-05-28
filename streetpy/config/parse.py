# -*- coding: utf-8 -*-

import streetpy.config.constants as const


# -----------------------
# OSM parsing functions


def osm_config_for_mode(conf, mode):
    """Returns the modal configuration for a mode"""

    configs = [
        conf.WALKWAYS,
        conf.CYCLEWAYS,
        conf.BUSWAYS,
        conf.DRIVEWAYS,
        conf.RAILWAYS,
    ]

    for c in configs:
        if c["mode"] == mode:
            return c


def osm_modal_filter(conf, mode, filter_type):
    """Extract dictionary for mode, filter type is 'keep' or 'exclude'"""

    c = osm_config_for_mode(conf, mode)
    res = {}

    if filter_type == "keep":
        f_list = [
            v
            for k, v in c.items()
            if k
            not in [
                "mode",
                "replace",
                "no",
                "no_infrastructure",
                "yes_designated",
                "map_highway",
                "map_service",
            ]
        ]
    elif filter_type == "exclude":
        f_list = [v for k, v in c.items() if k == "no"]

    for val in f_list:
        for k, v in val.items():
            if k not in res:
                res[k] = []
            if type(v) is list:
                res[k].extend(v)
            else:
                res[k].append(v)
    return res


def osm_modal_columns(conf, mode):
    """List of column names to extract for a mode"""
    d = osm_config_for_mode(conf, mode)
    return list(
        {
            col
            for k, v in d.items()
            for col in v
            if k not in ["mode", "replace", "map_highway", "map_service"]
        }
    )


# -----------------------
# speed parsing functions


def mode_speed_config(conf, mode):
    """
    return all possible mode names
    """
    consts = [
        conf.WALK_SPEED,
        conf.BIKE_SPEED,
        conf.TRANSIT_SPEED,
        conf.DRIVE_SPEED,
        conf.RAIL_SPEED,
    ]

    return [k for k in consts if k["mode"] == mode][0]


def speed_defaults(conf, country):

    res = conf.SPEED_DEFAULTS_CAR
    if country is None or country not in conf.COUNTRY_MODIFIER_CAR.keys():
        return res

    for k, v in conf.COUNTRY_MODIFIER_CAR[country].items():
        if k in res.keys():
            res[k] = v
        else:
            res[const.HIGHWAY][k] = v
    return res
