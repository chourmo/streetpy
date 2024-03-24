# -*- coding: utf-8 -*-

import geopandas as gpd
import numpy as np
import pandas as pd
import scipy as sp
import shapely as sh

COORD_EQUAL_ATOL = 1e-6  # the distance below which coordinates are considered equal


# ------------------
# Geometry manipulation
# ------------------


def reverse(geom):
    """ return the geometries of a GeoSeries in reverse direction
    """
    geom = gdf.geometry.values.data
    return sh.reverse(geom)


def _cumulative_length(coords):
    """cumulative length along a coordinates array"""
    dists = np.sqrt(np.sum((coords - np.roll(coords, 1, axis=0)) ** 2, axis=1))
    dists.iloc[0] = 0
    return np.cumsum(dists)

def _line_interpolate_point(geometry, distance, normalized):
    """ waiting for a geopandas integration
    interpolate points at distance
    see shapely function definition
    """

    new_pts = sh.line_interpolate_point(geometry.values.data, distance.to_numpy(), normalized)
    new_coords = sh.get_coordinates(new_pts)
    res = pd.DataFrame(new_coords, columns=["x", "y"], index=geometry.index)
    
    return res


def insert_point(geometry, distance, normalized=False):
    """
    Insert a point to a linestring geometry at a distance
    Args:
        geometry : a GeoSeries
        distance : a Series, with same index as geom
        normalized : if True, distance are between 0 and 1,
                     else distance if between 0 and geom length
    Returns:
        a GeoSeries with same index as geom
    """

    if not geometry.index.equals(distance.index):
        raise ValueError("geometry and distance must share index")

    pts = geometry.reset_index(drop=True).get_coordinates()
    
    # distance from one point to the next, as if one line
    pts["_pos"] = _cumulative_length(pts[["x", "y"]])

    # new points at distance
    new_pts = _line_interpolate_point(geometry.reset_index(drop=True), distance, normalized)

    # distance on global linestring
    new_pts["_pos"] = (
        distance.to_numpy() + pts["_pos"].groupby(level=0).min().to_numpy()
    )

    pts = pd.concat([pts, new_pts], axis=0)

    pts.index.name = "_ix"
    pts = pts.reset_index().sort_values(["_ix", "_pos"])
    
    pts = pts.drop_duplicates(subset=["_ix", "_pos"])
    pts = pts.set_index("_ix")

    res = sh.linestrings(
        coords=pts[["x", "y"]].to_numpy(), indices=pts.index.to_numpy()
    )

    return gpd.GeoSeries(res, index=geometry.index)


def _substring(geometry, starts, ends, normalized=False):
    """
    Cut linestrings geometries between starts and ends length
    points corresponding to starts and ends must exist in geometry
    """

    pts = geometry.reset_index(drop=True).get_coordinates()

    pts["_pos"] = _cumulative_length(pts[["x", "y"]])
    geom_start = pts["_pos"].groupby(level=0).min()

    if normalized:
        geo_len = geometry.geom.length
        pts["_start_pos"] = starts.reset_index(drop=True) * geo_len + geom_start
        pts["_end_pos"] = ends.reset_index(drop=True) * geo_len + geom_start
    else:
        pts["_start_pos"] = starts.reset_index(drop=True) + geom_start
        pts["_end_pos"] = ends.reset_index(drop=True) + geom_start

    pts = pts.loc[
        pts._pos.between(
            pts._start_pos - COORD_EQUAL_ATOL, pts._end_pos + COORD_EQUAL_ATOL
        )
    ]

    res = sh.linestrings(
        coords=pts[["x", "y"]].to_numpy(), indices=pts.index.to_numpy()
    )

    return res


def sub_linestring(geoms, starts=None, ends=None, normalized=False):
    """
    Cut linestrings between starts and ends distance

    Args :
        geoms : a Linestring GeoSeries
        start: optional Series of length to cut line after, replace nans by 0
        end: optional Series of length to cut line before, replace nans by 1 or length
        normalized: boolean, starts and ends are between 0 and 1

        drop geometries if start=end

    Returns:
        a new GeoSeries
    """
    gtypes = geoms.geom_type.value_counts()
    if len(gtypes) != 1 or gtypes.index[0] != "LineString":
        raise TypeError("Geometry must only contain LineString")

    df = geoms.copy()

    if starts is not None and ends is not None and len(df.loc[starts > ends]) > 0:
        raise ValueError("Starts must be smaller than ends")

    if starts is None:
        starts = pd.Series(0, index=geoms.index)
    if ends is None:
        if normalized:
            ends = pd.Series(1, index=geoms.index)
        else:
            ends = df.geometry.length

    if len(df.loc[starts > ends]) > 0:
        raise ValueError("Starts must be smaller than ends")

    starts = starts.fillna(0)
    if normalized:
        ends = ends.fillna(1)
    else:
        ends = ends.fillna(df.geometry.length)

    df = insert_point(df, starts, normalized=normalized)
    df = insert_point(df, ends, normalized=normalized)
    df = _substring(df, starts, ends)

    return df

def remove_duplicated_points(gdf):
    ''' remove duplicated points in linestring or polygon '''

    if 'Point' in gdf.geom_type:
        raise ValueError("Cannot remove duplicated point from points geometries")

    geoms = gdf.geometry.values.data
    simplified = sh.set_precision(geoms, grid_size=0.001)
    return gpd.GeoSeries(pd.Series(simplified, index=gdf.index), crs=gdf.crs)


# ------------------
# Arc bearings at intersection
# ------------------

def _bearing_angles(x, y):
    """return numpy array of bearings in degrees"""
    d = np.degrees(np.arctan2(x, y))
    return np.where(d < 0, d + 360, d)


def bearings(df, distance=0.1, reverse=False):
    """
    Calculate angle with north of segment

    Args:
        df : a LineString GeoSeries
        distance : distance for second point as percentage of linestring
        reverse : boolean, if True return bearings from end of linestring
    Returns:
        a Series of angles in radians for each node
    """

    geotypes = df.geom_type.drop_duplicates()

    if len(geotypes) > 1 or geotypes.values[0] != "LineString":
        raise ValueError("Dataframe must only contain Linestrings")

    if reverse:
        start = df.geometry.interpolate(1, normalized=True)
        end = df.geometry.interpolate(-1*distance, normalized=True)

    else:
        start = df.geometry.interpolate(0)
        end = df.geometry.interpolate(distance, normalized=True)

    return _bearing_angles(end.x - start.x, end.y - start.y)


def ordered_bearings(df, distance=0.1):
    """
    Return a dataframe of edges at node id in clockwise bearing order
    """

    res = df.net.expand_edges(source="source", target="target", drop=True)
    if res.index.name is None:
        raise ValueError("dataframe index must have a name")
    else:
        edge_ix = res.index.name

    st = res[["source"]].reset_index()
    st["angle"] = bearings(res.geometry, distance)

    end = res[["target"]].reset_index()
    end[edge_ix] = end[edge_ix] * -1
    end["angle"] = bearings(res.geometry, distance, reverse=True)

    res = pd.concat([st.set_index("source"), end.set_index("target")])
    res.index.name = "node_id"

    res = res.sort_values(["node_id", "angle"])

    return res

# ------------------
# Create polygons inside street arcs
# ------------------

def _map_directed_edge(edgeid, mapper):
    if edgeid < 0:
        return -1 * mapper[-1 * edgeid]
    return mapper[edgeid]


def _polygonize(df, mapper):

    edges = df.set_index("to_edge")["from_edge"].to_dict()
    traversed = set([])
    results = []

    for edge in edges.keys():

        if edge in traversed:
            continue

        polygon = [edge]
        traversed.add(edge)
        cursor = edges[-edge]

        while cursor != edge:

            # remove deadends
            if len(polygon) > 0 and cursor == -1 * polygon[-1]:
                polygon = polygon[:-1]
            else:
                polygon.append(cursor)

            traversed.add(cursor)
            cursor = edges[-cursor]

        if len(polygon) >= 2:
            results.append([_map_directed_edge(x, mapper) for x in polygon])

    return results


def polygon_edges(df):
    """
    Find inner polygons inside graph edges
    """

    # create an internal edge index, starting from 1
    # negative indexes are edges in reverse direction

    edges = df.copy()
    if edges.index.name is None:
        edges.index.name = "_reference_ix"
    ref_edge_ix = edges.index.name
    edges = edges.reset_index()
    edges.index = edges.index + 1
    edges.index.name = "from_edge"
    edge_ix = edges.index.name

    mapper = edges[ref_edge_ix].to_dict()

    # create a graph between edges in counter clock wise order

    nodes = ordered_bearings(edges)

    nodes["to_edge"] = nodes[edge_ix].shift(1)
    nodes["diff_angle"] = nodes["angle"] - nodes["angle"].shift(1)

    # connect first edge to last edge
    first_mask = ~nodes.index.duplicated(keep="first")
    last_mask = ~nodes.index.duplicated(keep="last")
    nodes.loc[first_mask, "to_edge"] = nodes.loc[last_mask, edge_ix].values
    nodes.loc[first_mask, "diff_angle"] = (
        nodes.loc[first_mask, "angle"] + 360 - nodes.loc[last_mask, "angle"].values
    )

    nodes["to_edge"] = nodes["to_edge"].astype(int)

    polygons = _polygonize(nodes, mapper)

    return pd.Series(polygons)


def polygon_geometries(df, edges):
    """ Create a GeoSeries of polygons from a list of edges """

    res = edges.copy()
    res.index.name = "poly_ix"
    res = res.to_frame("edges")
    res2 = res.explode(column="edges").reset_index()

    # geometry
    reverse_geom_mask = res2["edges"] < 0
    res2["edges"] = res2["edges"].abs()

    res2 = pd.merge(res2, df[["geometry"]], left_on="edges", right_index=True, how="left")
    res2 = res2.set_geometry("geometry", crs=df.crs)

    res2.loc[reverse_geom_mask, "geometry"] = sh.reverse(res2.loc[reverse_geom_mask, "geometry"])

    res["geometry"] = res2.groupby("poly_ix")["geometry"].apply(lambda x: sh.polygonize(list(x)))
    res = res.set_geometry("geometry", crs=df.crs).explode(index_parts=False)
    return  res.reset_index(drop=True)