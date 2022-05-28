# -*- coding: utf-8 -*-


def update_category(df, mask, update_value):
    """
    update content of a categorical column, if not a category, update values in place
    """

    if df.dtype != "category":
        df.loc[mask] = update_value
        return df

    res = df.astype("str").copy()
    res.loc[mask] = update_value
    return res.astype("category")


# -------------------
# Errors
# -------------------


class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class NoNetworkError(Error):
    """Exception raised if no graph setup"""

    def __init__(self, message):
        self.message = "graph has not been set up, use set_edge_graph or set_node_graph"


class NotImportedError(Error):
    """Exception raised if no graph setup"""

    def __init__(self, message, library):
        self.message = "{0} has not been imported".format(library)
