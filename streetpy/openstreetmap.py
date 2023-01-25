# -*- coding: utf-8 -*-

import os.path

import netpandas as npd
import pandas as pd

import streetpy.attributes as attr
# import streetpy constants and default configurations
import streetpy.config.constants as const
import streetpy.config.osm_tags as osm_conf
import streetpy.config.parse as parse
import streetpy.config.speeds as spd_conf
from streetpy.spatial import reverse
from streetpy.streetpy import is_accessible, is_designated, street_mode_columns

try:
    from osmdatapy import OSM, Query
    HAS_OSM = True
except ImportError:
    HAS_OSM = False
    pass

OSMID = "osmid"


def streets_from_osm(
    path_or_place,
    crs,
    modes=True,
    access_level="public",
    track=False,
    construction=False,
    drive_right=True,
    config=osm_conf,
    country=None,
):
    """
    Create an undirected netpandas and geopandas dataframe from osm data, without self loops

    Attributes :
        path_or_place : path of a pbf file or place name
        crs : spatial projection in projected coordinate space
        modes : if True fetch all modes or if list of modes to fetch : drive, bike, transit, walk, rail
        source : name of source column
        target : name of target column
        access_level : filter streets by access tag, "all" or "permissive" (non-private) or "public" (non private or permissive)
        track : keep tracks or non-urban streets
        construction : keep proposed or in construction streets
        config : a configuration .py object similar to config.osm_tags
        country: used for OSM default values
    """

    if not HAS_OSM:
        raise ValueError("Pyrosm must be installed")

    if os.path.exists(path_or_place):
        osm_data = OSM(filepath=path_or_place)
    else:
        osm_data = OSM(place=path_or_place)

    # validate modes
    if type(modes) == bool and modes:
        modes = const.mode_list()
    if not set(modes).issubset(const.mode_list()):
        raise ValueError("modes must be a subset of {1}".format(const.mode_list()))

    # parse base data
    edge_query = _edge_query(config, modes, access_level, track, construction)
    df = osm_data.query(edge_query)
    df = df.drop(columns=["osmtype"]).to_crs(crs)

    # drop all content for track and construction
    if not track:
        df = _drop_columns(df, config.TRACK_EXCLUDE)
    if not construction:
        df = _drop_columns(df, config.CONSTRUCTION_EXCLUDE)

    # rename highways and railways
    df[const.HIGHWAY] = df[const.HIGHWAY].replace(to_replace=config.REPLACE_HIGHWAYS)
    if "rail" in modes:
        df[const.RAILWAY] = df[const.RAILWAY].replace(
            to_replace=config.REPLACE_RAILWAYS
        )

    df = _convert_junction(df, config.REPLACE_JUNCTIONS)
    df = _convert_oneway(df)

    # make a modal query and get data
    query = _modal_query(df[OSMID].drop_duplicates().tolist(), modes)
    for mode in modes:
        query.append_tags(parse.osm_modal_columns(config, mode))
        query.append_keep(parse.osm_modal_filter(config, mode, "keep"))
        query.append_keep(parse.osm_modal_filter(config, mode, "exclude"))

    df_modal = osm_data.query(query)

    for mode in modes:
        df = _append_modal(df, df_modal, config, mode, drive_right)

    # at least one mode must be used, walk is bidirectional
    if "walk" in modes:
        df = df.drop(columns=["walk_r"])
    df = df.dropna(subset=street_mode_columns(df), how="all")

    df = _bikes_on_walkways(df)

    # set as netpandas, keep source and target columns
    df = npd.set_network(df, directed=False, source="source", target="target")

    # remove self looping edges : source=target
    df = df.loc[~df.net.is_loop()]

    # if rail in modes, drop unused or abondoned railways if not designated to bike
    df = _filter_abandoned_railways(df)

    # remove services not used by another mode
    df = _filter_service(df, config, access_level)

    # filter footways as sidewalks and paths
    df = _filter_sidewalks(df, modes)
    df = _filter_paths(df, modes)

    # find urban arcs
    if len(modes) == 1 and const.RAILWAY in modes:
        mask = ~df[const.RAILWAY].isna()
    elif const.RAILWAY in modes:
        mask = (~df[const.RAILWAY].isna()) | (df[const.HIGHWAY] != "motorway")
    else:
        mask = df.highway != "motorway"
    df[const.URBAN] = attr.urban(df.loc[mask])
    df[const.URBAN] = df[const.URBAN].fillna(False)

    # set default maxspeed column
    df = _default_maxspeed(df, spd_conf, country=country)

    # remove non connected edges, except for rail mode
    df = _filter_disconnected(df)

    # convert to categories
    if len(modes) == 1 and const.RAILWAY in modes:
        cols = [const.RAILWAY]
    elif const.RAILWAY in modes:
        cols = [const.HIGHWAY, const.RAILWAY]
    else:
        cols = [const.HIGHWAY]
    cols = cols + street_mode_columns(df)
    df[cols] = df[cols].astype("category")

    # reorder rows on same osmid to match source to target
    df = npd.sort_arcs(df, "osmid")

    return df.reset_index(drop=True)


def osm_excluding_zones(
    path_or_place, crs, config=osm_conf, access_level="public", min_area=None
):
    """
    Get zones to exclude some streets from

    Attributes:
        path_or_place : path of a pbf file or place name
        crs : spatial projection in projected coordinate space
        config : a configuration .py object similar to config.osm_tags
        access_level :  "all" or "permissive" (non-private) or "public" (non private or permissive)
        min_area : drop zones under this area, default to None

    Returns:
        a GeoDataframe with columns from config, and access_level
    """


    if not HAS_OSM:
        raise ValueError("Pyrosm must be installed")
        
    osm_data = OSM(path_or_place)

    if access_level == "all":
        return None

    df = osm_data.query(_zone_query(config, access_level))
    df = df.drop(columns=["osmtype"])

    df = df.loc[df.geom_type.isin(["Polygon", "MultiPolygon"])]
    df = df.to_crs(crs)

    if min_area is not None:
        df = df.loc[df.geometry.area >= min_area]

    # add a access_level, permissive or restrictive depending on access_level
    # filter restrictive
    df["access_level"] = "permissive"

    l = [(k, v) for k, v in config.RESTRICTED_ZONES.items() if k in df.columns]
    for k, v in l:
        df.loc[df[k].isin(v), "access_level"] = "restrictive"

    # remove superposing polygons
    df = df.reset_index(drop=True).dissolve(by="access_level")
    df = df.reset_index().explode(index_parts=False).reset_index(drop=True)

    return df


# -------------------------------------------------
# OSM queries


def _edge_query(config, modes, access_level, track, construction):
    """Create the OSM base edge query with geometry and topology"""

    if len(modes) == 1 and modes[0] == "rail":
        nec_tags = [const.RAILWAY]
        tags = [
            const.HIGHWAY,
            const.RAILWAY,
            "oneway",
            "junction",
            "service",
            "maxspeed",
        ]
    elif "rail" in modes:
        nec_tags = [const.HIGHWAY, const.RAILWAY]
        tags = [
            const.HIGHWAY,
            const.RAILWAY,
            "oneway",
            "junction",
            "service",
            "maxspeed",
        ]
    else:
        nec_tags = [const.HIGHWAY]
        tags = [const.HIGHWAY, "oneway", "junction", "service", "maxspeed"]

    query = Query(
        ways=True,
        must_tags=nec_tags,
        tags=tags,
        exclude=config.STREET_EXCLUDE,
        keep_first=False,
        geometry=True,
        topology=True,
    )

    if access_level not in ["all", "permissive", "public"]:
        raise ValueError("access level must be all, permissive or public")

    if not track:
        query.append_exclude(config.TRACK_EXCLUDE)
    if not construction:
        query.append_exclude(config.CONSTRUCTION_EXCLUDE)

    if access_level == "permissive":
        query.append_exclude(config.PRIVATE_ACCESS)
    if access_level == "public":
        query.append_exclude(config.PRIVATE_ACCESS)
        query.append_exclude(config.PERMISSIVE_ACCESS)

    # keep transit and bike even if exclude
    query.append_keep(parse.osm_modal_filter(config, "bike", "keep"))
    query.append_keep(parse.osm_modal_filter(config, "transit", "keep"))

    return query


def _modal_query(way_ids, modes):
    """Create an OSM query for mode"""

    if len(modes) == 1 and modes[0] == "rail":
        nec_tags = [const.RAILWAY]
        tags = ["highway", const.RAILWAY]
    elif "rail" in modes:
        nec_tags = ["highway", const.RAILWAY]
        tags = ["highway", const.RAILWAY]
    else:
        nec_tags = ["highway"]
        tags = ["highway"]

    query = Query(
        ways=True, tags=tags, necessary_tags=nec_tags, way_ids=way_ids, flat=True
    )

    return query


def _zone_query(config, access_level):
    """Create an OSM query for permissible or private access_level"""

    tags = []
    if access_level == "permissive":
        tags.extend(config.RESTRICTED_ZONES.keys())
    if access_level == "public":
        tags.extend(config.PERMISSIVE_ZONES.keys())
    tags = list(set(tags))

    query = Query(
        ways=True, relations=True, tags=tags, geometry=True, necessary_tags=tags
    )

    if access_level == "permissive":
        query.append_keep(config.RESTRICTED_ZONES)
    if access_level == "public":
        query.append_keep(config.PERMISSIVE_ZONES)
        query.append_keep(config.RESTRICTED_ZONES)

    return query


# ---------------------------------------------------
# data transformation or filtering


def _drop_columns(df, exclude):
    """Drop df rows from exclude dictionary of column:value"""
    res = df.copy()

    for col, val in exclude.items():
        if col in df.columns:
            res = res.loc[~res[col].isin(val)]
    return res


def _append_modal(df, df_modal, config, mode, drive_right):
    """
    Update dataframe with content for mode based on config

    Attributes:
        df : dataframe to update with modal content
        osm_data : osm data
        config : osm tags config dictionary
        mode : mode name
        drive_right: boolean of driving direction
    """
    HWAY = const.HIGHWAY
    mode_conf = parse.osm_config_for_mode(config, mode)
    name = mode_conf["mode"]
    name_r = name + const.REV_SUFFIX
    forward, backward = ("right", "left")
    if ~drive_right:
        forward, backward = ("left", "right")

    res = pd.merge(
        df_modal.reset_index(),
        df[[OSMID, "oneway"]].drop_duplicates(OSMID),
        on=OSMID,
        how="left",
    )

    res = _convert_junction(res, config.REPLACE_JUNCTIONS)

    # modal accessibility

    res[[name, name_r]] = pd.NA

    if "both" in mode_conf:
        up = _update_dict(res, mode_conf["both"])
        res.loc[~up.isna(), name] = up
        res.loc[~up.isna(), name_r] = up

    if "oneway" in mode_conf:
        up = _update_dict(res, mode_conf["oneway"])
        res.loc[~up.isna(), name] = up
        res.loc[~res.oneway, name_r] = up

    if "left" in mode_conf:
        up = _update_dict(res, mode_conf["left"])
        if drive_right:
            res.loc[~up.isna(), name_r] = up
        else:
            res.loc[~up.isna(), name] = up

    if "right" in mode_conf:
        up = _update_dict(res, mode_conf["right"])
        if drive_right:
            res.loc[~up.isna(), name] = up
        else:
            res.loc[~up.isna(), name_r] = up

    if "forward" in mode_conf:
        up = _update_dict(res, mode_conf["forward"])
        res.loc[~up.isna(), name] = up

    if "backward" in mode_conf:
        up = _update_dict(res, mode_conf["backward"])
        res.loc[~up.isna(), name_r] = up

    if "replace" in mode_conf:
        res[name] = res[name].replace(mode_conf["replace"])
        res[name_r] = res[name_r].replace(mode_conf["replace"])

    if "no" in mode_conf:
        up = _update_dict(res, mode_conf["no"])
        res.loc[(~up.isna()) & (res[name].isna()), name] = "no"
        res.loc[~up.isna() & (res[name_r].isna()), name_r] = "no"

    if "yes_designated" in mode_conf:
        up = _update_dict(res, mode_conf["yes_designated"])
        res.loc[(~up.isna()) & (res[name] == "yes"), name] = "designated"
        res.loc[(~up.isna()) & (res[name_r] == "yes"), name_r] = "designated"

    if "no_infrastructure" in mode_conf:
        up = _update_dict(res, mode_conf["no_infrastructure"])
        res.loc[(~up.isna()) & (~res[name].isna()) & (res[name] != "no"), name] = "yes"
        res.loc[
            (~up.isna()) & (~res[name_r].isna()) & (res[name_r] != "no"), name_r
        ] = "yes"

    res = pd.merge(df, res[[OSMID, name, name_r]], on=OSMID, how="left")

    # defaults as oneway column
    res.loc[res[name].isna(), name] = "yes"
    res.loc[(res[name_r].isna()) & (~res.oneway), name_r] = "yes"

    # remap services, must be done before mapping highways
    if "map_service" in mode_conf:
        for k, v in mode_conf["map_service"].items():
            res.loc[(res["service"] == k) & (res[HWAY] == "service"), HWAY] = v

    # remap on highway value
    if "map_highway" in mode_conf:
        for k, v in mode_conf["map_highway"].items():
            res.loc[(res[HWAY] == k) & (res[name] == "yes"), name] = v
            res.loc[(res[HWAY] == k) & (res[name_r] == "yes"), name_r] = v

    res.loc[res[name] == "no", name] = pd.NA
    res.loc[res[name_r] == "no", name_r] = pd.NA

    return res


def _update_dict(df, conf):
    """Returns a Series with values from df and a conf dictionnary of colum:values"""

    res = pd.Series(data=[pd.NA] * df.shape[0], index=df.index)
    for k, v in [(k, v) for k, v in conf.items() if k in df.columns]:
        if len(v) > 0:
            res.loc[df[k].isin(v)] = df[k]
        else:
            # empty list, return all values if not na
            res.loc[~df[k].isna()] = df[k]
    return res


def _convert_oneway(df):
    """
    Convert oneways to bool, fillna roundabout as oneway
    revert source, target and geometry if oneway == -1
    """

    res = df.copy()

    # reverse -1 oneway
    mask = df.oneway == "-1"
    df_s = df.loc[mask, "source"].copy()
    df.loc[mask, "source"] = res["target"]
    res.loc[mask, "target"] = df_s
    res.loc[mask,  df.geometry.name] = reverse(res.loc[mask,  df.geometry.name])

    # force roundabouts to oneway
    res.loc[(res[const.JUNCTION] == "roundabout") & (res.oneway.isna()), "oneway"] = "1"

    # map values
    res["oneway"] = res["oneway"].map({"yes": True, "1": True, "-1":True}).fillna(False)

    return res


def _convert_junction(df, to_replace):
    """
    Prepare junction column=
        - convert _link highways to simple text
        - add link to junction column
        - replace junction content based on config
    """

    res = df.copy()
    links = df[const.HIGHWAY].str.split("_link", expand=True)

    if links.shape[1] > 1:
        links = links.rename(columns={0: "col0", 1: "col1", 2: "col2"})
        mask = ~links["col1"].isna()
        res.loc[mask, const.HIGHWAY] = links["col0"]
        res.loc[mask, const.JUNCTION] = "link"
    res[const.JUNCTION] = res[const.JUNCTION].replace(to_replace=to_replace)

    return res


def _bikes_on_walkways(df):
    """
    replace bike or bike_r to footway or pedestrian if
    walk is steps, pedestrian or footway and bikes or bike_r = 'yes'
    """
    name, name_r = const.mode_columns("bike")
    walk_n, _ = const.mode_columns("walk")

    if name not in df.columns or name_r not in df.columns or "walk" not in df.columns:
        return df

    mask = df[walk_n].isin(["pedestrian", "footway", "steps"])
    df.loc[(df[name] == "yes") & (mask), name] = df[walk_n]
    df.loc[(df[name_r] == "yes") & (mask), name_r] = df[walk_n]
    return df


def _filter_abandoned_railways(df):
    """Drop abandoned railways if not designated to transit or bikes"""

    if const.RAILWAY not in df.columns:
        return df

    m1 = ~df[const.RAILWAY].isin(["disused", "abandoned", "dismantled"])
    m2 = (is_designated(df, mode="bike")) | (is_designated(df, mode="transit"))

    # if abandoned and used by rail or transit, set railway to na
    df.loc[(~m1) & (m2), const.RAILWAY] = pd.NA

    return df.loc[m1 | m2]


def _filter_disconnected(df):
    """
    keep largest component and keep all rail edges
    """

    if const.RAILWAY not in street_mode_columns(df):
        return df.net.filter_by_component()

    edge_name = df.net.name

    df_rail = df.loc[~df[const.RAILWAY].isna()]
    df = df.loc[df[const.RAILWAY].isna()]
    df = pd.concat([df.net.filter_by_component(), df_rail]).sort_index()

    return npd.set_network(df, directed=False, edge=edge_name)


def _filter_service(df, config, access_level):
    """
    Transfer some service values to highway and drop service column
    if access_level is not all and street is not designated to transit or bike
    drop rows with services in highway
    """
    if "service" not in df.columns:
        return df

    res = df.copy()

    if access_level != "all":
        mask_desi = is_designated(df, "bike") | is_designated(df, "transit")
        res = res.loc[mask_desi | (res.highway != "service")]

    return res.drop(columns="service")


def _filter_sidewalks(df, modes):
    """
    Filter footways as sidewalks or crossing and not use by bikes
    """
    if "walk" not in modes or "bike" not in modes or const.HIGHWAY not in df.columns:
        return df

    m1 = df[const.HIGHWAY] == "footway"
    m2 = ~df["walk"].isin(["sidewalk", "crossing", "access_aisle"])
    m3 = is_accessible(df, mode="bike")
    return df.loc[(m2) | (m3)]


def _filter_paths(df, modes):
    """
    convert streets with highway=path and bicycle as designated
    to either highway=cycleway
    drop other rows with highway=path
    """

    if "bike" not in modes or const.HIGHWAY not in df.columns:
        return df

    mask = (df[const.HIGHWAY] == "path") & (is_designated(df, "bike"))
    df.loc[mask, const.HIGHWAY] = "cycleway"
    return df.loc[df[const.HIGHWAY] != "path"]


def _default_maxspeed(df, speed_conf, country=None):
    """
    set default values to maxspeed in a dataframe, returns the full dataframe
    highway and urban column content may be modified by maxspeed values with country code
    """

    # convert texts with country codes
    df = _maxspeed_remove_country(df)

    # convert text as units
    df[const.SPEED] = attr.convert_unit(df[const.SPEED])

    # create speed configuration with country
    conf = parse.speed_defaults(speed_conf, country)

    # set if urban
    df.loc[(df[const.URBAN]) & (df[const.SPEED].isna()), const.SPEED] = conf["urban"]

    # set values by highway
    for k, v in conf["highway"].items():
        df.loc[(df[const.HIGHWAY] == k) & (df[const.SPEED].isna()), const.SPEED] = v

    df[const.SPEED] = pd.to_numeric(df[const.SPEED], errors="coerce")
    df[const.SPEED] = df[const.SPEED].fillna(conf["else"])

    return df


def _maxspeed_remove_country(df):
    """
    convert COUNTRYCODE:text maxspeed column
        if text is urban or rural, change urban column
        else change to na
    """
    country = df[const.SPEED]
    country = country.loc[(~country.isnull()) & (country.str.contains(":"))]
    country = country.str[3:]

    # text is urban or rural
    df.loc[country.loc[country == "urban"].index, const.URBAN] = True
    df.loc[country.loc[country == "rural"].index, const.URBAN] = False

    df.loc[country.index, const.SPEED] = pd.NA

    return df
