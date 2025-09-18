def compute_bounds_from_geojson(geojson):
    """
    Calcula los límites (bounds) de un objeto GeoJSON.
    Devuelve [[min_lat, min_lon], [max_lat, max_lon]] o None si no hay datos.
    """
    def _collect_lonlat(coords, acc):
        if isinstance(coords[0], (float, int)) and isinstance(coords[1], (float, int)):
            acc.append((coords[0], coords[1]))
        else:
            for c in coords:
                _collect_lonlat(c, acc)

    points = []
    if geojson is None:
        return None
    if geojson.get("type") == "FeatureCollection":
        for feat in geojson.get("features", []):
            g = feat.get("geometry") if feat.get("type") == "Feature" else feat
            if g and g.get("coordinates"):
                _collect_lonlat(g.get("coordinates"), points)
    elif geojson.get("type") == "Feature":
        g = geojson.get("geometry")
        if g and g.get("coordinates"):
            _collect_lonlat(g.get("coordinates"), points)
    elif geojson.get("coordinates"):
        _collect_lonlat(geojson.get("coordinates"), points)
    if not points:
        return None
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]
