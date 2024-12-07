# -*- coding: utf-8 -*-

import numpy as np # type: ignore
import pandas as pd # type: ignore
import scipy as sp # type: ignore

import streetpy.config.constants as const
import streetpy.config.parse as parse

# -------------------------------------------------
# Units


def convert_unit(df, units=const.UNIT_CONV):
    """
    convert a text Series with units to a Float Series with units conversion applied
    non convertible text are converted to nan

    Attributes:
        unit : text of the unit and float multiplier to default OSM unit (m, km/h)
               only simple units are implemented : format float, space, unit

    Result:
        pandas Series
    """

    # replace None by na
    res = df.loc[~df.isnull()]
    res = res.str.split(expand=True).rename(columns={0: "num", 1: "unit"})

    if "unit" not in res.columns:
        return res["num"]

    res["num"] = pd.to_numeric(res["num"], errors="coerce")
    res["_conv"] = res["unit"].map(units).fillna(1)

    return res["num"] * res["_conv"]


# -------------------------------------------------
# Attribute and elevation


def urban(ndf, distance=50, size=10, cluster_size=100):
    """
    Identify edges grouped and close enough to be considered in an urban context

    Args:
        ndf : a net/geo dataframe
        see DBSCAN algorythm for distance and size arguments
        cluster_size : minimum number of nodes to form a cluster

    Returns:
        a Series aligned on df, with cluster number if is urban
    """

    # find pt clusters by DBSCAN
    nodes = ndf.net.node_clusters(distance, size)

    # minimum cluster size
    clusters = nodes.value_counts()
    clusters = clusters.loc[clusters > cluster_size]

    nodes = nodes.loc[nodes.isin(clusters.index)]

    # edges in a cluster
    res = ndf.loc[ndf.net.has_any_nodes(nodes.index)]

    # find connected components as cluster numbers
    res = res.net.edge_components().reindex(ndf.index)
    res = res.iloc[:, 0]
    edge_clusters = res.value_counts()
    edge_clusters = edge_clusters.loc[edge_clusters > cluster_size]

    return res.isin(edge_clusters.index)


# -------------------------------------------------
# Travel Time


def base_travel_time(streets, mode, speed_conf):
    """
    returns travel time Series based on a speeds column and a mode
    """

    speed = streets[const.SPEED].copy()
    length = streets.geometry.length

    config = parse.mode_speed_config(speed_conf, mode)

    if config["replace_maxspeed"] is None:
        if config["max"] is not None:
            speed.loc[speed > config["max"]] = config["max"]
    elif isinstance(config["replace_maxspeed"], (int, float)):
        speed.loc[:] = config["replace_maxspeed"]
    else:
        raise ValueError("replace_maxspeed value in config must be None or numeric")

    if len(speed.loc[(speed == 0) | (speed.isna())]) > 0:
        raise ValueError("Speed cannot be 0 or na")

    df = length * 3.6 / speed
    return df


def _slow_speed_interpolate(t, s, m, h):
    """
    returns a speed ratio
    t : np.array of time points
    s : slow speed for 3rd, 4th, 7th and 8th time points
    m : mid day speed for 5th and 6th time points
    h : hour in minutes to interpolate to

    returns a value between 0.0 and 1.0
    """

    val = np.ones(t.shape)
    val[2:7] = s
    val[4:5] = m
    f = sp.interpolate.interp1d(t, val)

    return f(h)


def time_ratio(slow_speed, time, max_slow=0.4, midday_min=0.9, midday_max=0.5):
    """
    returns the time speed ratio, float between 0 and 1,

    Args:
        slow_speed : Series of speed ratio compared to max speed
        time : tuple of hour and minutes
    """
    if midday_min < midday_max:
        raise ValueError("midday_min must be bigger than midday_max")

    # key time points for interpolation function
    t = np.array(
        [x * 60 for x in [0.0, 5.0, 7.0, 11.0, 11.5, 13.0, 14, 18.0, 21.0, 24.0]]
    )

    # array of minimum speeds at peak hours
    df = slow_speed.clip(lower=max_slow).to_frame("_s")

    # array of midday speeds, interpolated between midday min and midday max
    a = (1 - df["_s"]) / (midday_min - midday_max)
    df["_m"] = a * df["_s"] + 1 - midday_min * a
    df["_m"] = df["_m"].clip(lower=df["_s"], upper=1.0)

    hour = time[0] * 60 + time[1]

    df = df.apply(lambda x: _slow_speed_interpolate(t, x["_s"], x["_m"], hour), axis=1)

    return df
