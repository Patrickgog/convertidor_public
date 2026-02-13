import json
from typing import Any, Dict

from app_pkg.export.html_templates import create_mapbox_html, leaf_tpl


def build_project_index_html(
    geojson: Dict[str, Any],
    map_type: str,
    bounds: Any,
    title: str,
    folder_name: str,
) -> str:
    if map_type == "mapbox":
        return create_mapbox_html(geojson, title=title, folder_name=folder_name, grouping_mode="type")
    return (
        leaf_tpl
        .replace("__TITLE__", title)
        .replace("__GEOJSON__", json.dumps(geojson))
        .replace("__BOUNDS__", json.dumps(bounds))
        .replace("__CENTER_LAT__", str((bounds[0][0] + bounds[1][0]) / 2 if bounds else -12.0))
        .replace("__CENTER_LON__", str((bounds[0][1] + bounds[1][1]) / 2 if bounds else -77.0))
    )


__all__ = ["build_project_index_html"]
