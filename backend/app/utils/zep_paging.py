"""Legacy paging helpers kept for import compatibility.

Graphiti-backed services no longer use SDK pagination. These functions raise a
clear error if an older integration path still calls them.
"""


def fetch_all_nodes(*args, **kwargs):
    raise RuntimeError("Legacy graph pagination is unavailable after the Graphiti migration.")


def fetch_all_edges(*args, **kwargs):
    raise RuntimeError("Legacy graph pagination is unavailable after the Graphiti migration.")
