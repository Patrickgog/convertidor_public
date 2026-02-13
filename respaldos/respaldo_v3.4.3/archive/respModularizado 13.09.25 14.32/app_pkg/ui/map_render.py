import folium
from streamlit_folium import st_folium
import streamlit as st
from typing import Dict, Any


def render_map(geojson_data: Dict[str, Any], group_by: str = "type") -> None:
    m = folium.Map(location=[-2.0, -79.0], zoom_start=10, tiles=None, prefer_canvas=True)
    folium.TileLayer("OpenStreetMap", name="Calles").add_to(m)
    folium.TileLayer("CartoDB Positron", name="Positron").add_to(m)
    folium.TileLayer("Esri.WorldImagery", name="Satelital").add_to(m)

    grouped = {}
    for feature in geojson_data.get("features", []):
        props = feature.get("properties", {})
        key = props.get("layer", "SinGrupo") if group_by == "layer" else props.get("type", "SinGrupo")
        group = grouped.setdefault(str(key), {"non_text": [], "texts": [], "points": []})
        if props.get("type") == "text":
            group["texts"].append(feature)
        elif feature.get("geometry", {}).get("type") == "Point":
            group["points"].append(feature)
        else:
            group["non_text"].append(feature)

    groups = {}
    for key, parts in grouped.items():
        fg = folium.FeatureGroup(name=str(key), show=True)
        fg.add_to(m)
        if parts["non_text"]:
            try:
                fc = {"type": "FeatureCollection", "features": parts["non_text"]}
                style_function = None
                if key == "track":
                    style_function = lambda x: {"color": "#e31a1c", "weight": 3, "opacity": 0.8}
                elif key == "route":
                    style_function = lambda x: {"color": "#1f78b4", "weight": 3, "opacity": 0.8, "dashArray": "5, 10"}
                gj = folium.GeoJson(fc, name=f"{key}_geom", style_function=style_function)
                gj.add_to(fg)
                groups[key] = gj
            except Exception:
                pass
        for feat in parts["points"]:
            try:
                coords = feat.get("geometry", {}).get("coordinates", None)
                if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    folium.CircleMarker(location=[lat, lon], radius=3, color="#2c7fb8", fill=True, fill_opacity=0.9).add_to(fg)
            except Exception:
                continue
        for feat in parts["texts"]:
            try:
                coords = feat.get("geometry", {}).get("coordinates", None)
                props = feat.get("properties", {})
                if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    label = str(props.get("text", ""))
                    if label:
                        folium.Marker(
                            location=[lat, lon],
                            icon=folium.DivIcon(html=f"<div style='font-size:12px;color:#0d6efd;font-weight:600;'>{label}</div>")
                        ).add_to(fg)
                    else:
                        folium.Marker(location=[lat, lon]).add_to(fg)
            except Exception:
                continue

    try:
        all_bounds = []
        for gj in groups.values():
            try:
                b = gj.get_bounds()
                if b:
                    all_bounds.extend(b)
            except Exception:
                pass
        if all_bounds:
            m.fit_bounds(all_bounds)
    except Exception:
        pass

    folium.LayerControl(position="topright").add_to(m)
    st_folium(m, width=None, height=650)


__all__ = ["render_map"]
