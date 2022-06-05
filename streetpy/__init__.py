"""A python library to analyse streets dataframes"""

from streetpy import read_streets, save_streets, street_columns, street_mode_columns, to_single_mode, is_valid_street, is_accessible, is_designated
from matching import match_trajectories
from simplification import simplify, filter_zones
from openstreetmap import get_osm_data, streets_from_osm, osm_excluding_zones
from shortest_path import shortest_path, shortest_paths

# Handle versioneer
from ._version import get_versions
versions = get_versions()
__version__ = versions['version']
__git_revision__ = versions['full-revisionid']
del get_versions, versions

from . import _version
__version__ = _version.get_versions()['version']
