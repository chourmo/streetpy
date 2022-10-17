# -*- coding: utf-8 -*-

import geopandas as gpd
import netpandas as npd
import networkx as nx
import pandas as pd

from .shortest_path import shortest_path, shortest_paths
from .spatial import sublinestring, substring


def match_trajectories(
    trajectories, streets, distance, weight, k_nearest=8, graph=None
):
    """
    Match a trajectory GeoSeries to an ordered list of street arcs

    Args:
        streets : a streetpy compatible dataframe
        trajectories : a GeoSeries of Points, index as trajectory order
        distance : distance to connect points to streets, in trajectories CRS
        weight : streets column to find shortest path between points
        k_nearest : integer or None, maximal number of candidate edges to match
        graph: optional pandana graph extracted from streets

    Results: a DataFrame of street arcs with same index as trajectories
        stop : stop number corresponding to trajectories rows
        street edges
        streets geometry
    """

    if not isinstance(trajectories, gpd.geoseries.GeoSeries):
        raise ValueError("trajectories must be a GeoSeries")

    gtypes = trajectories.geom_type.value_counts()
    if len(gtypes) > 1 or gtypes.head(1).index.values != "Point":
        raise ValueError("trajectories must only contain Point")
        
    if graph is None:
        graph = streets.net.graph("pandana", attributes=[weight])

    s, t = "_source", "_target"
    df_s = streets.net.expand_edges(source=s, target=t)
    df_s["length"] = df_s.geometry.length

    pts = trajectories.copy()
    pts.index.name = "_tid"  # trajectory id
    pts = pts.reset_index()
    pts["stop"] = pts.groupby("_tid").cumcount()  # stop number in trajectory

    # find closests edges to each trajectory point, distance column
    pts = df_s.net.edges_at_distance(
        pts, distance=distance, k_nearest=k_nearest, edge_attrs=[weight, s, t, "length"]
    )

    # drop shape_ids with one point not connected
    pts = pts.loc[_incomplete_trajectories(pts, trajectories)]

    # projet point on edge
    pts[["proj_length", "pt_wt"]] = _edge_weights(
        pts.geometry,
        pts.set_geometry("edge_geom"),
        distances=pts["distance"],
        weights=pts[weight],
    )

    pts = pts.drop(columns=["distance", pts.geometry.name, "edge_geom"]).reset_index(
        drop=True
    )

    # make transition graphs
    trans = _transition_graph(pts, df_s, s, t, weight=weight, graph=graph)

    # find shortest path on arcs
    res = trans.groupby("_tid").apply(
        lambda x: _solve_path(x, "prob", "arc_id", "arc_id_n", "stop")
    )

    res = npd.expand_paths(res, trans).reset_index(drop=True)

    # expand to street edges
    res = npd.expand_paths(res[["_tid", "stop", "path"]], df_s, "path").reset_index(
        drop=True
    )

    # last edge in each trajectory is stop number + 1
    ix = res.groupby("_tid").tail(1).index
    res.loc[ix, "stop"] = res["stop"] + 1

    # add projected length for stop on arc to cut, for first edge of each stop
    res = pd.merge(
        res,
        pts[["_tid", "stop", s, t, "proj_length"]],
        on=["_tid", "stop", s, t],
        how="left",
    )
    res.loc[
        ~res.index.isin(res.groupby(["_tid", "stop"]).head(1).index), "proj_length"
    ] = pd.NA

    # set index to same values as trajectories
    res = res.set_index("_tid")
    res.index.name = trajectories.index.name

    # drop missing geometries
    res = res.dropna(subset=[df_s.geometry.name])

    res = _split_at_stops(
        res[["stop", "proj_length", s, t, df_s.geometry.name]],
        source=s,
        target=t,
        cut_length="proj_length",
        stop="stop",
    )

    res[s] = res[s].astype(int)
    res[t] = res[t].astype(int)

    res = npd.set_network(res, source=s, target=t, directed=True)

    return res


def _incomplete_trajectories(pts, traj):
    """
    return subset of pts if drop trajectories in df if some points are missing
    trajectory ids are in traj index and in _tid column of pts
    stop_number is the stop position number
    """

    ix_traj = traj.index.value_counts()
    ix_pts, ix_traj = pts.groupby("_tid")["stop"].nunique().align(ix_traj)
    ix_traj = ix_traj.loc[ix_traj == ix_pts]

    return pts["_tid"].isin(ix_traj.index)


def _edge_weights(pt_geom, edge_geom, distances, weights, proximity_factor=5):
    """
    find emmission probability depending on distance between point and arc
    emmission probability must be larger than 0, add a minimum value

    proximity_factor : multiplicator to favor edges close to stops
    """

    dist = edge_geom.project(pt_geom).to_frame("proj_length")
    dist["pt_wt"] = distances * weights / edge_geom.length

    return dist[["proj_length", "pt_wt"]]


def _transition_graph(pts, netdf, source, target, weight, graph=None):
    """
    Create transitions from stop to stop and add weights
    returns a netpandas dataframe
    """

    df = pts.copy()
    df.index.name = "arc_id"
    df = df.reset_index()
    df["_next_stop"] = df["stop"].add(1)

    # all possible paths from one stop to the other on same _tid
    df = pd.merge(
        df,
        df,
        left_on=["_tid", "_next_stop"],
        right_on=["_tid", "stop"],
        how="inner",
        suffixes=["", "_n"],
    )

    df = df.drop(columns=["_next_stop", "_next_stop_n"]).reset_index(drop=True)

    # find shortest path from target to next source,
    # except for transitions on same edge or reverse edge

    mask = (df[source] == df[source + "_n"]) & (df[target] == df[target + "_n"])

    spath = shortest_paths(
        netdf,
        df.loc[~mask, target],
        df.loc[~mask, source + "_n"],
        weight=weight,
        distance=True,
        graph=graph,
    )

    df.loc[~mask, "dist"] = spath["distance"]
    df.loc[~mask, "path"] = spath["path"]

    # drop if transition on same edge and point positions are reversed
    df = df.loc[(~mask) | (df.proj_length <= df.proj_length_n)].copy()

    # drop arc if on missing shortest_path solution
    df = df.loc[(~mask) | (df.path.isna())].copy()

    # path between consecutive have path but no distance, fill with 0
    df.loc[(~mask) & (df.dist.isna()), "dist"] = 0

    # TODO : drop trajectory if one fully missing transition

    # transition probability, use all weighted values
    df["proj_wt"] = df["proj_length"] * df[weight] / df["length"]
    df["proj_wt_n"] = df["proj_length_n"] * df[weight + "_n"] / df["length_n"]

    # if transition on same street edge :
    if len(df.loc[mask]) > 0:
        df.loc[mask, "prob"] = df.eval("pt_wt + pt_wt_n + proj_wt_n - proj_wt")
        df.loc[mask, "path"] = df.loc[mask][[source, target]].apply(list, axis=1)

    # else :
    if len(df.loc[~mask]) > 0:
        df.loc[~mask, "prob"] = df[weight] + df.eval(
            "pt_wt + pt_wt_n + dist - proj_wt + proj_wt_n"
        )
        df.loc[~mask, "path"] = npd.add_paths(df[source], df["path"])

        # add end node to last transition if on unique arc
        max_stop = df.groupby("_tid")["stop"].transform(max)
        df.loc[(~mask) & (df.stop == max_stop), "path"] = npd.add_paths(
            df["path"], df[target + "_n"]
        )

    # convert to netpandas graph
    df = npd.set_network(
        df, directed=True, source="arc_id", target="arc_id" + "_n", drop=False
    )

    return df


def _solve_path(df, weight, source, target, sequence):
    """
    find shortest path on the transition graph
    """

    # restore network in group
    graph = npd.set_network(df, directed=True, source=source, target=target, drop=False)

    # connect start
    start_pts = df.loc[df[sequence] == df[sequence].min(), source]
    graph, start = npd.connect_nodes(graph, start_pts, fill_values=0, ending="start")

    # connect end
    end_pts = df.loc[df[sequence] == df[sequence].max(), target]
    graph, end = npd.connect_nodes(graph, end_pts, fill_values=0, ending="end")

    # use networkx to solve path as long as pandana must have coordinates
    G = graph.net.graph("networkx", attributes=[weight])
    
    try:
        _, res = nx.bidirectional_dijkstra(G, start, end, weight)
        return res[1:-1]
    except:
        return None


def _split_at_stops(df, source, target, cut_length, stop):
    """
    split linestring on cut_length, geometries are associated to the following stop
    """
    # trajectory id in dataframe
    if df.index.name is None:
        ixname = "_ix"
    else:
        ixname = df.index.name
    res = df.reset_index().copy()

    # segment order
    res.index.name = "_segment"
    res = res.reset_index()

    geo = df.geometry.name
    res["_length"] = res.geometry.length
    res["_end"] = res[cut_length].shift(-1)

    # extend last cut to geometry length
    m = (res[source] != res[source].shift(-1)) | (res[target] != res[target].shift(-1))
    res.loc[m, "_end"] = res["_length"]

    # extend missing first cut to 0
    res.loc[(res[cut_length].isna()) & (res._end == res._length), "_end"] = pd.NA

    # add first segment of cut arc, assign to previous stop
    df2 = res.loc[(~res._end.isna())].drop_duplicates([ixname, source, target])
    df2["_end"] = df2[cut_length]
    df2[cut_length] = 0
    df2[stop] = df2[stop] - 1

    res = pd.concat([res, df2]).sort_values(["_segment", stop]).reset_index(drop=True)

    # drop first and last subsegment of each trajectory
    ix = res.groupby("shape_id").tail(1).index
    res = res.loc[(~res.index.isin(ix.values)) & (res[stop] != -1)]

    # stop geometries before point
    res[stop] = res[stop] + 1
    
    # drop geometries if cut_length = end_length
    res = res.loc[(res[cut_length].isna()) |(res[cut_length]!=res["_end"])]
    
    # cut geometries
    res[geo] = substring(res.geometry, res[cut_length], res['_end'])
    
    res = res.set_index(ixname)
    if df.index.name is None:
        res.index.name = None

    return res.drop(columns=[cut_length, "_segment", "_length", "_end"])    