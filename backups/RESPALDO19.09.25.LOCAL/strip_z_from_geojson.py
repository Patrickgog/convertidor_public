def strip_z_from_geojson(geojson):
    """
    Elimina la coordenada Z de todos los puntos en un GeoJSON.
    """
    def _strip(coords):
        if isinstance(coords, (list, tuple)):
            if len(coords) == 3 and all(isinstance(x, (int, float)) for x in coords):
                return coords[:2]
            return [_strip(c) for c in coords]
        return coords

    if geojson is None:
        return None
    import copy
    gj = copy.deepcopy(geojson)
    if gj.get("type") == "FeatureCollection":
        for feat in gj.get("features", []):
            geom = feat.get("geometry")
            if geom and geom.get("coordinates"):
                geom["coordinates"] = _strip(geom["coordinates"])
    elif gj.get("type") == "Feature":
        geom = gj.get("geometry")
        if geom and geom.get("coordinates"):
            geom["coordinates"] = _strip(geom["coordinates"])
    elif gj.get("coordinates"):
        gj["coordinates"] = _strip(gj["coordinates"])
    return gj
