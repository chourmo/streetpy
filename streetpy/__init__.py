"""A python library to analyse streets dataframes"""

from streetpy.matching import match_trajectories as match_trajectories

from streetpy.openstreetmap import osm_excluding_zones as osm_excluding_zones
from streetpy.openstreetmap import streets_from_osm as  streets_from_osm

from streetpy.shortest_path import shortest_path as shortest_path
from streetpy.shortest_path import shortest_paths as shortest_paths

from streetpy.simplification import filter_zones as filter_zones
from streetpy.simplification import simplify as simplify

from streetpy.streetpy import is_accessible as is_accessible
from streetpy.streetpy import is_designated as is_designated
from streetpy.streetpy import is_valid_street as is_valid_street
from streetpy.streetpy import read_streets as read_streets
from streetpy.streetpy import save_streets as save_streets
from streetpy.streetpy import street_columns as street_columns
from streetpy.streetpy import street_mode_columns as street_mode_columns
from streetpy.streetpy import to_single_mode as to_single_mode

from streetpy.spatial import bearings as bearings
from streetpy.spatial import ordered_bearings as ordered_bearings
from streetpy.spatial import polygon_edges as polygon_edges
from streetpy.spatial import polygon_geometries as polygon_geometries
