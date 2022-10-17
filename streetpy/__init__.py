"""A python library to analyse streets dataframes"""

# Handle versioneer
from ._version import get_versions
from .matching import match_trajectories
from .openstreetmap import osm_excluding_zones, streets_from_osm
from .shortest_path import shortest_path, shortest_paths
from .simplification import filter_zones, simplify
from .streetpy import (is_accessible, is_designated, is_valid_street,
                       read_streets, save_streets, street_columns,
                       street_mode_columns, to_single_mode)

versions = get_versions()
__version__ = versions['version']
__git_revision__ = versions['full-revisionid']
del get_versions, versions

from . import _version

__version__ = _version.get_versions()['version']
