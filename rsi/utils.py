def get_item(iterable_or_dict, index, default=None):
    """Return iterable[index] or default if IndexError is raised."""
    try:
        return iterable_or_dict[index]
    except (IndexError, KeyError):
        return default
