# -*- coding: utf-8 -*-

import pandas as pd
import geopandas as gpd
import netpandas as npd

try:
    import pandana as pnd

    HAS_PANDANA = True
except:
    HAS_PANDANA = False


# base function if pandana is installed


def shortest_path(streets, source, target, weight=None, graph=None):
    """
    Compute shortest path on graph between source and target nodes
    Weight values must all be positives

    Internaly uses pandana

    Args:
        streets: a directed streetpy dataframe
        source: node id to start the path from
        target: node id  to end the path
        weight: an optional column name, if None use length
        graph : an optional pandana graph extracted from streets

    Returns:
        path : a list of node ids
    """

    if graph is not None:
        res = graph.shortest_path(source, target, weight)

    elif weight is not None and len(streets.loc[streets[weight] < 0]) > 0:
        raise ValueError("Weights must all be positive")

    else:
        G = streets.net.graph("pandana", attributes=[weight])
        res = G.shortest_path(source, target, weight)

    return res.tolist()


def shortest_paths(streets, sources, targets, weight, distance=False, graph=None):
    """
    Compute shortest paths between sources and targets series, sharing an index

    Args:
        streets : a streetpy directed dataframe
        sources: a series of integer nodes as sources for shortest path
        targets: a series of integer nodes as targets for shortest path
        weight: a street column of positive numerical values
        distance: return the total weighted distance from source to target
        graph: an optional pandana graph extracted from streets

    Returns:
        a dataframe with same index as sources, source and target columns,
        and a node path column
    """

    s, t = "_s", "_t"

    if len(sources) != len(targets):
        raise ValueError("sources and targets must have the same length")
    if not sources.index.equals(targets.index):
        raise ValueError("sources and targets must have same the same index")

    # make od pairs dataframe
    od = sources.to_frame(s)
    od.loc[targets.index, t] = targets
    od = od.drop_duplicates()

    if graph is not None:
        od["path"] = graph.shortest_paths(od[s], od[t], weight)
    elif weight is not None and len(streets.loc[streets[weight] < 0]) > 0:
        raise ValueError("Weights must all be positive")
    else:
        G = streets.net.graph("pandana", attributes=[weight])
        od["path"] = G.shortest_paths(od[s], od[t], weight)

    # expand to duplicated (source, target) pairs
    if len(od) < len(sources):
        res = sources.to_frame(s)
        res.loc[targets.index, t] = targets
        od = pd.merge(res, od, on=[s, t], how="left")

        # merge resets index, copy back
        od.index = sources.index.copy()

    if distance:
        od["distance"] = npd.paths_distance(od["path"], streets, weight)
        return od[["distance", "path"]]

    return od["path"]
