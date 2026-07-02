def running_max(values):
    """Running maximum at each index of `values`."""
    if not values:
        return []
    result = []
    current = values[0]
    for v in values:
        current = max(current, v)
        result.append(current)
    return result
