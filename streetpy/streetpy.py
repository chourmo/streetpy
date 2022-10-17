# -*- coding: utf-8 -*-

"""
Generic functions to create and modify streetpy dataframes
"""
import shutil
import tempfile
from pathlib import Path

import geopandas as gpd
import netpandas as npd
from pandas.api.types import is_categorical_dtype, is_integer_dtype

import streetpy.attributes as attrs
import streetpy.config.constants as const
import streetpy.config.speeds as spd_conf
import streetpy.simplification as simp


def read_streets(path, source, target, directed):
    """
    returns a streetpy dataframe from a spatial dataframe and set as netpandas
    """

    df = gpd.read_file(path)

    if source not in df.columns:
        raise ValueError("{0} must be a column".format(source))
    if target not in df.columns:
        raise ValueError("{0} must be a column".format(target))

    if not is_integer_dtype(df[source]):
        df[source] = df[source].astype(int)
    if not is_integer_dtype(df[target]):
        df[target] = df[target].astype(int)

    df = npd.set_network(df, directed=directed, source=source, target=target)

    return df


def save_streets(df, path, source="source", target="target", compress=False):
    """
    save streets to a spatial format
    convert categories to text and expand edges to source and target columns
    optionaly zip the resulting file or files
    """

    res = df.net.expand_edges(source=source, target=target, drop=True)

    # convert categories
    for c in [c for c in res.columns if is_categorical_dtype(res[c])]:
        res[c] = res[c].astype(str)
        res[c] = res[c].str.replace("nan", "")
        res[c] = res[c].str.replace("None", "")

    if not compress:
        res.to_file(path)

    else:
        d = tempfile.TemporaryDirectory()

        p = Path(path)
        res.to_file(p.joinpath(d.name, p.name))

        res = shutil.make_archive(d.name, "zip", root_dir=d.name)

        shutil.copyfile(res, p)
        p.rename(p.with_suffix(".zip"))

    return None


def street_columns(streets):
    """
    returns streetpy specific columns in a streets dataframe
    """

    c = const.streetpy_base_columns() + const.streetpy_optional_columns(streets)
    c = c + street_mode_columns(streets)
    c = c + [streets.geometry.name, streets.net.name]

    return c


def street_mode_columns(df):
    """Return a list of valid modal columns"""
    return [c for c in const.mode_columns() if c in df.columns]


def to_single_mode(streets, refid, mode, speed_conf=spd_conf):
    """
    extract and simplify a single mode directed fully connected dataframe,
    with time between edges, edges are merged between crossings
    and no duplicated edges (same source, target)

    Args :
        streets : a street net/geo/dataframe
        mode : mode name
        speed_conf : speed configuration to estimate time and edge weights

    Results:
        a directed street net/geo/dataframe with columns:
            - edges
            - 'time' as time to traverse edge
            - 'weight' weighting ratio based on road hierarchy
            - geometry if geometry argument is not None
    """

    df = streets.copy()

    m_cols = [c for c in const.mode_columns(mode) if c in streets.columns]
    if len(m_cols) == 0:
        raise ValueError("Mode {0} not in streets")

    # filter edges by mode and drop other modal columns
    # some modes as walk may not have a reverse direction
    if len(m_cols) == 1:
        m_cols.append(m_cols[0] + "_r")
        df[m_cols[0] + "_r"] = df[m_cols[0]]

    m_col, m_col_r = m_cols[0], m_cols[1]
    df = df.loc[(~df[m_col].isna()) | (~df[m_col_r].isna())].copy()
    df = df.drop(columns=list(set(street_mode_columns(streets)) - set(m_cols)))

    # Simplify dataframe
    df = simp.simplify(df, refid)

    # To directed edges
    df = df.net.to_directed(forward=m_col, backward=m_col_r, split_mid_nodes=True)

    # Base travel time for each edge
    df[const.TIME] = attrs.base_travel_time(df, mode, speed_conf)

    # Weighted travel time based on mode column content

    # Saturated travel time depending on day type and hour
    
    # drop duplicated edges, keep smallest weight
    df = df.sort_values([streets.net.name, const.TIME])
    df = df.drop_duplicates([streets.net.name])
    df = df.sort_index()

    return df[[refid, const.TIME, streets.net.name, df.geometry.name]]


# ----------------------------------------------------
# content tests


def is_valid_street(df):
    """
    check if the dataframe is a valid streetpy dataframe :
        - is both a geopandas and net dataframe
        - has necessary column names from confi/constants : SPEED and HIGHWAY columns
    returns a boolean
    """

    if not isinstance(df, gpd.GeoDataFrame):
        return False

    if not npd.is_netdf(df):
        return False

    if len([c for c in const.streetpy_base_columns() if c in df.columns]) == 0:
        return False

    return True


def is_accessible(df, mode):
    """returns True if edge is accessible by a mode"""
    if mode not in const.mode_list():
        raise ValueError("Not a valid mode")

    if const.is_mode_bidirectional(mode):
        return ~df[mode].isna()
    else:
        name_r = mode + const.REV_SUFFIX
        return (~df[mode].isna()) | (~df[name_r].isna())


def is_designated(df, mode):
    """returns True if edge is designated (not na and not yes) by a mode"""
    if mode not in const.mode_list():
        raise ValueError("Not a valid mode")

    res = (~df[mode].isna()) & (df[mode] != "yes")
    
    if const.is_mode_bidirectional(mode):
        return res

    name_r = mode + const.REV_SUFFIX
    return res | ((~df[name_r].isna()) & (df[name_r] != "yes"))
