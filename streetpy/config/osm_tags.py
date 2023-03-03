# -*- coding: utf-8 -*-

# --------------------------------------------------------
# FILTERING ZONES

# remove if access is not permissive, query zones
PERMISSIVE_ZONES = {
    "landuse": [
        "cemetery",
        "industrial",
        "retail",
        "commercial",
        "garages",
        "allotments",
        "quarry",
    ],
    "leisure": ["park", "garden", "sports_centre"],
    "amenity": ["university"],
}

RESTRICTED_ZONES = {"landuse": ["military"]}

ZONE_CONFIG = {
    "permissive": {
        "highway": [
            "service",
            "pedestrian",
            "footway",
            "steps",
            "unclassified",
        ]
    },
    "restrictive": {
        "highway": [
            "service",
            "pedestrian",
            "footway",
            "unclassified",
            "path",
            "track",
            "road",
        ]
    },
}


# --------------------------------------------------------
# STREETS

# --------------------------------------------------------
# attributes

HIGHWAY_TAGS = [
    "bridge",
    "tunnel",
    "access",
    "amenity",
    "area",
    "bicycle",
    "cyclestreet",
    "bicycle_road",
    "bus",
    "busway",
    "busway:both",
    "busway:left",
    "busway:right",
    "bus:lanes",
    "bus:lanes:forward",
    "bus:lanes:backward",
    "cycleway",
    "cycleway:lane",
    "cycleway:right",
    "cycleway:left",
    "cycleway:both",
    "foot",
    "footway",
    "highway",
    "junction",  # for roundabounts
    "lanes:psv",
    "lanes:psv:forward",
    "lanes:psv:backward",
    "maxspeed",
    "motorcar",
    "motor_vehicle",
    "oneway",
    "psv",
    "service",
    "sidewalk",
    "vehicle",
]

# extra columns with highway attributes
HIGHWAY_ATTRS = [
    "bridge",
    "lanes",
    "lit",
    "maxheight",
    "name",
    "overtaking",
    "segregated",
    "smoothness",
    "surface",
    "tunnel",
    "width",
]

RAILWAY_TAGS = [
    "funicular",
    "light_rail",
    "monorail",
    "narrow_gauge",
    "preserved",
    "rail",
    "subway",
    "tram",
]

REPLACE_HIGHWAYS = {
    "alley": "residential",
    "living_street": "residential",
    "road": "residential",
    "unclassified": "residential",
}

REPLACE_RAILWAYS = {"narrow_gauge": "rail"}
REPLACE_JUNCTIONS = {"circular": "roundabout", "mini_roundabout":"roundabout", "true":"link"}

# --------------------------------------------------------
# exclude

STREET_EXCLUDE = {
    "highway": [
        "abandoned",
        "disused",
        "virtual",
        "no",
        "corridor",  # in building
        "elevator",  # in building
        "escalator",  # in building
        "bus_stop",  # transit
        "platform",  # transit
    ],
    "service": [
        "crossover",
        "yard",
        "spur",
        "siding",  # rails
        "irrigation",
        "slipway",  # waterways
    ],
    "railway": [
        "platform",
        "disused",
        "abandoned",
        "razed",
        "subway_entrance",
        "platform_edge",
        "halt",
        "turntable",
        "depot",
        "roundhouse",
        "razed",
        "level_crossing",
        "switch",
        "signal",
        "buffer_stop",
        "crossing",
        "platform",
        "station",
        "tram_stop",
        "workshop",
        "technical_center",
        "technical_station",
        "miniature",
    ],
    "rail": ["subway_entrance"],
    "area": ["yes"],
    "type": ["multipolygon"],
    "footway": ["sidewalk", "crossing", "access_aisle"],
}

TRACK_EXCLUDE = {
    "highway": ["track", "bridleway", "via-ferrata"],
    "informal": ["yes"],
    "access": ["forestry", "agricultural"],
    "vehicle": ["forestry", "agricultural"],
}

CONSTRUCTION_EXCLUDE = {
    "highway": ["proposed", "construction"],
    "railway": ["proposed", "construction"],
}

PERMISSIVE_ACCESS = {
    "access": ["permissive"],
    "vehicle": ["permissive"],
}

PRIVATE_ACCESS = {
    "service": [
        "drive-through",
        "driveway",
        "escape",
        "emergency_access",
        "emergency_access_point",
        "parking",
        "parking_aisle",
        "private",
        "rest_area",
    ],
    "highway": ["emergency_access_point", "rest_area", "escape", "raceway", "services"],
    "access": [
        "customers",
        "delivery",
        "military",
        "permit",
        "private",
        "residents",
        "forestry",
        "agricultural",
    ],
    "vehicle": [
        "customers",
        "delivery",
        "military",
        "permit",
        "private",
        "residents",
    ],
    "motorcar": ["private", "customers"],
    "motor_vehicle": ["private", "customers"],
    "vehicle": ["forestry", "agricultural"],
}


# --------------------------------------------------------
# modal data

# if value in dict is empty list, all values are to be considered

# mode : mode name
# map_highway : optional dictionnary, if highway has key, replace modal content by value
# map_service : optional dictionnary, if service has key, replace highway by value
# both: key:list of values accessible streets in both direction, independent of oneway
# oneway : key:list of values accessible streets in same direction that driving oneway
# left : key:list of values accessible streets in left of street, depends on driving direction
# right : key:list of values, accessible streets in right of street, depends on driving direction
# forward : key:list of values, accessible streets in street direction
# right : key:list of values, accessible streets in reverse street direction
# no : key:list of values if mode is forbidden except if values in other key:values
# replace: dict of values in osm data to replace


WALKWAYS = {
    "mode": "walk",
    "both": {
        "highway": ["pedestrian", "footway", "steps", "track", "path"],
        "sidewalk": ["both", "left", "right"],
        "foot": ["yes", "designated"],
    },
    "no": {
        "railway": [],
        "highway": ["motorway", "trunk", "cycleway"],
        "sidewalk": ["no", "none"],
        "footway": ["no", "none", "sidewalk"],
        "foot": ["use_sidepath"],
    },
    "replace": {
        "both": "yes",
        "left": "yes",
        "right": "yes",
        "separate": "footway",
    },
}


CYCLEWAYS = {
    "mode": "bike",
    "map_highway": {"cycleway": "designated"},
    "both": {
        "cycleway:both": [
            "yes",
            "lane",
            "share_busway",
            "shared",
            "shared_lane",
            "track",
            "shoulder",
        ],
        "oneway:bicycle": ["no"],
    },
    "oneway": {
        "bicycle": ["yes", "designated"],
        "cycleway": [
            "yes",
            "lane",
            "share_busway",
            "shared",
            "shared_lane",
            "track",
            "shoulder",
        ],
        "cycleway:lane": [
            "yes",
            "lane",
            "share_busway",
            "shared",
            "track",
            "exclusive",
            "shoulder",
        ],
        "cyclestreet": ["yes", "designated", "permissive"],
        "bicycle_road": ["yes", "designated"],
        "oneway:bicycle": ["yes"],
    },
    "left": {
        "cycleway:left": [
            "yes",
            "lane",
            "share_busway",
            "shared",
            "shared_lane",
            "track",
            "shoulder",
        ],
    },
    "right": {
        "cycleway:right": [
            "yes",
            "lane",
            "share_busway",
            "shared",
            "shared_lane",
            "track",
            "shoulder",
        ],
    },
    "backward": {
        "cycleway": [
            "opposite",
            "opposite_lane",
            "opposite_share_busway",
            "opposite_shared",
            "opposite_track",
        ],
    },
    "no": {
        "railway": RAILWAY_TAGS,
        "highway": ["motorway", "trunk", "steps", "pedestrian", "footway"],
        "bicycle": ["no", "none"],
    },
    "yes_designated":{"highway":["footway"]},
    "no_infrastructure": {
        "cycleway": ["no", "none"],
        "bicycle_road": ["no", "none"],
        "cyclestreet": ["no", "none"],
    },
    "replace": {
        "opposite_lane": "lane",
        "opposite_track": "track",
        "opposite_share_busway": "share_busway",
    },
}


BUSWAYS = {
    "mode": "transit",
    "map_highway": {"busway": "lane", "bus_guideway": "lane"},
    "map_service": {"busway": "busway", "bus": "busway"},
    "both": {
        "busway:both": ["yes", "lane"],
        "lanes:psv": ["2"],
    },
    "oneway": {
        "busway": ["yes", "lane"],
        "bus:lanes": ["yes"],
        "psv": ["yes", "bus", "designated"],
        "highway": ["bus_guideway", "busway"],
    },
    "left": {"busway:left": ["yes", "lane"]},
    "right": {"busway:right": ["yes", "lane"]},
    "forward": {"bus:lanes:forward": [], "lanes:psv:forward": []},
    "backward": {
        "busway": ["opposite", "opposite_lane"],
        "bus:lanes:backward": [],
        "lanes:psv:backward": [],
    },
    "no": {
        "highway": [
            "footway",
            "pedestrian",
            "cycleway",
            "steps",
            "path",
        ],
        "railway": RAILWAY_TAGS,
        "bus": ["no", "none"],
    },
    "no_infrastructure": {
        "busway": ["no", "none"],
        "bus_guideway": ["no", "none"],
        "psv": ["no", "none"],
    },
    "replace": {
        "bus": "busway",
        "yes|designated": "designated",
        "designated|yes": "designated",
        "|designated": "designated",
        "||designated": "designated",
        "|||designated": "designated",
        "designated|": "designated",
        "designated||": "designated",
        "designated|||": "designated",
        "yes|yes|designated": "designated",
        "designated|yes|yes": "designated",
        "designated|permissive": "designated",
        "designated|no": "designated",
        "no|designated": "designated",
        "no|no|designated": "designated",
        "designated|no|no": "designated",
        "no|yes|designated": "designated",
        "designated|yes|no|": "designated",
        "1": "lane",
        "2": "lane",
    },
}


# for drive and rail, only no values
DRIVEWAYS = {
    "mode": "drive",
    "map_service": {"alley": "alley"},
    "no": {
        "access": ["no", "none"],
        "railway": [],
        "highway": [
            "bus",
            "bus_guideway",
            "busway",
            "cycleway",
            "footway",
            "pedestrian",
            "steps",
            "path",
        ],
        "motorcar": ["no", "none"],
        "motor_vehicle": ["no", "none"],
    },
}

RAILWAYS = {"mode": "rail", "no": {"highway": []}}
