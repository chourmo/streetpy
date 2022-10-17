# -*- coding: utf-8 -*-

import geopandas as gpd
import netpandas as npd
import pandas as pd

import streetpy.config.osm_tags as osm_tags
import streetpy.streetpy as st

MAX_ITER = 100


def simplify(streets, refid, deadend=False, size=None):
    """
    simplify a streetpy dataframe by removing and merging edges :
        - not connected to other edges
        - included in zones, with zone config
        - connected to self, or in arcs connected to self
        - in dead end arcs below a length
        - in arcs connecting edges only by pairs, if reference id is set to a column name, arcs can only contains same refid values

    Args:
        streets : a streetpy undirected dataframe
        refid : if not None, a column name of ids (ex. osmid)
        deadend : if True drop all dead ends, if False do not filter, if number filter to length
        size : if not None, minimum size of connected graph, else keep largest component

    Returns :
        a new streetpy dataframe
    """

    if streets.net.directed:
        raise ValueError("Streets must not be directed")

    df = streets.net.expand_edges(source="_s", target="_t")

    df["_length"] = df.geometry.length

    # filter graph size
    if type(size) == int or size is None:
        df = df.net.filter_by_component(size=size)

    df["_topoid"] = npd.no_self_loop_index(df, refid, "_s", "_t")
    df = npd.sort_arcs(df, "_topoid")

    s = -1
    i = 0

    while s != len(df) and i <= MAX_ITER:

        s = df.shape[0]
        i += 1
        df["_edgeid"] = npd.topological_edge_index(df, "_topoid", "_s", "_t")

        stats = _arc_statistics(df, "_edgeid", "_s", "_t", "_length")

        # deadends
        if type(deadend) == bool and deadend:
            deadend_ix = stats.loc[
                (stats._s_degree == 1) | (stats._t_degree == 1)
            ].index
        elif type(deadend) == int:
            deadend_ix = stats.loc[
                ((stats._s_degree == 1) | (stats._t_degree == 1))
                & (stats.length <= deadend)
            ].index
        else:
            deadend_ix = None

        # loops
        loop_ix = stats.loc[stats.source == stats.target].index

        if deadend_ix is None and len(loop_ix) > 0:
            df = df.loc[~df._edgeid.isin(loop_ix)]
        elif len(loop_ix) > 0:
            union_ix = loop_ix.union(deadend_ix)
            df = df.loc[(~df._edgeid.isin(union_ix))]
        elif len(loop_ix) == 0 and deadend_ix is not None:
            df = df.loc[(~df._edgeid.isin(deadend_ix))]

    # group arcs
    df["_edgeid"] = npd.topological_edge_index(df, "_topoid", "_s", "_t")
    df = npd.merge_arcs(df, arcid="_edgeid", source="_s", target="_t")

    return df.drop(columns=["_edgeid", "_topoid", "_length"])


def filter_zones(
    streets,
    zones,
    zone_config=osm_tags.ZONE_CONFIG,
    keep_bike=True,
    keep_transit=True,
    keep_rail=True,
):
    """
    Remove edges inside some zones (parks, retail...) depending on
    an access_level column and a configuration dictionnary

    Attributes :
        - df : a streetpy dataframe
        - zones : a geodataframe of polygons with an access_level column
        - zone_config : a dictionnary :
            - first level keys are access_levels
            - second level are df column names / values to exclude if in zones
        keep_bikes : boolean, always keep edges if is designated to bikes
        keep_transit : boolean, always keep edges if designated to transit
        keep_rail : boolea, always keep edges if designated to rail

    Results:
        a new streetpy dataframe
    """

    modes = st.street_mode_columns(streets)

    # make unique index
    res = streets.copy()
    res.index.name = "_index"
    res = res.reset_index()

    if streets.crs != zones.crs:
        res = res.to_crs(zones.crs)

    # filter streets to always keep designated
    mask = pd.Series([False] * len(res), index=res.index)
    if keep_rail and "rail" in modes:
        mask = mask | st.is_designated(res, "rail")
    if keep_bike and "bike" in modes:
        mask = mask | st.is_designated(res, "bike")
    if keep_transit and "transit" in modes:
        mask = mask | st.is_designated(res, "transit")

    df = res.loc[~mask]
    df = gpd.sjoin(
        df, zones[[zones.geometry.name, "access_level"]], predicate="intersects", how="left"
    )

    for k, v in zone_config.items():
        for col, values in v.items():
            df = df.loc[(df["access_level"] != k) | (~df[col].isin(values))]

    res = res.loc[(mask) | (res.index.isin(df.index))]
    res = res.set_index("_index")
    res.index.name = streets.index.name

    return res


def _arc_statistics(streets, arcid, source="_s", target="_t", length="_length"):

    # unneeded warning in _arc statistics
    pd.options.mode.chained_assignment = None

    nodes = streets.net.degree().to_frame("_s_degree")

    grp = streets.groupby(arcid)
    res = grp.agg(
        source=(source, "first"), target=(target, "last"), length=(length, sum)
    )
    res = res.join(nodes, on="source", how="left")
    res = res.join(
        nodes.rename(columns={"_s_degree": "_t_degree"}), on="target", how="left"
    )
    return res
