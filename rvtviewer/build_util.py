def g(o, *path, default=None):
    """navigate decoded record fields; transparently steps through pointer slots ('obj')"""
    for p in path:
        if isinstance(o, dict) and 'obj' in o and p not in o: o = o['obj']
        if isinstance(o, dict) and p in o: o = o[p]
        else: return default
    if isinstance(o, dict) and 'obj' in o: o = o['obj']
    return o
