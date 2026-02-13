import json
import folium
from streamlit_folium import st_folium
import streamlit as st
import os
from src.core.geometry.coordinate_utils import compute_bounds_from_geojson

def get_mapbox_token():
    """Retorna el token de Mapbox buscando en secretos, entorno o localmente."""
    # 1. Intentar desde st.secrets (Streamlit Cloud o local .streamlit/secrets.toml)
    try:
        if "MAPBOX_API_KEY" in st.secrets:
            return st.secrets["MAPBOX_API_KEY"]
    except:
        pass
    
    # 2. Intentar desde variables de entorno
    env_token = os.getenv("MAPBOX_API_KEY")
    if env_token:
        return env_token
        
    return None

def create_normal_html(geojson_data, title="Map Viewer", bounds=None, grouping_mode="type"):
    """Genera HTML con visor Leaflet normal con control de capas según modo de agrupamiento"""
    geojson_str = json.dumps(geojson_data)
    bounds_str = json.dumps(bounds) if bounds else "null"
    
    if grouping_mode.lower() == "layer":
        # Modo LAYER: Agrupar por layer del DXF
        html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title} - Map Viewer</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style> 
        html, body {{ height: 100%; margin: 0; }} 
        #map {{ height: 100vh; }} 
        .leaflet-control-layers-expanded {{ max-height: 60vh; overflow: auto; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const map = L.map('map', {{ preferCanvas: true }});
        
        // Capas base
        const calles = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: 'OpenStreetMap', maxZoom: 19 }});
        const positron = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png', {{ attribution: 'CartoDB Positron', maxZoom: 19 }});
        const satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ attribution: 'Esri', maxZoom: 19 }});
        const baseMaps = {{
            "Calles": calles,
            "Positron": positron,
            "Satelital": satelite
        }};
        
        // Agregar capa base por defecto
        positron.addTo(map);

        // GeoJSON y grupos por LAYER
        const data = {geojson_str};
        function groupByLayer(features) {{
            const groups = {{}};
            features.forEach(f => {{
                const layer = (f.properties && f.properties.layer) ? f.properties.layer : 'Default';
                if (!groups[layer]) groups[layer] = [];
                groups[layer].push(f);
            }});
            return groups;
        }}
        
        const grouped = groupByLayer(data.features || []);
        const overlayMaps = {{}};
        
        // Colores por layer
        const layerColors = ['#ff0000', '#0000ff', '#00ff00', '#ffff00', '#ff00ff', '#00ffff', '#ff8000', '#8000ff', '#0080ff', '#ff0080'];
        let colorIndex = 0;
        
        Object.keys(grouped).forEach(layer => {{
            const feats = grouped[layer];
            const color = layerColors[colorIndex % layerColors.length];
            colorIndex++;
            
            let layerGroup = L.layerGroup();
            
            feats.forEach(feature => {{
                const type = (feature.properties && feature.properties.type) ? feature.properties.type : 'unknown';
                
                       if (type === 'point' || type === 'block') {{
                           const [lon, lat] = feature.geometry.coordinates;
                           const marker = L.circleMarker([lat, lon], {{
                               radius: 4, 
                               color: color, 
                               fillColor: color,
                               fillOpacity: 0.8
                           }});
                           layerGroup.addLayer(marker);
                       }} else if (type === 'text') {{
                           const [lon, lat] = feature.geometry.coordinates;
                           const label = feature.properties && feature.properties.text ? feature.properties.text : '';
                           const marker = L.marker([lat, lon], {{
                               icon: L.divIcon({{ 
                                   className: '', 
                                   html: `<div style='font-size:12px;color:${{color}};font-weight:600;background:white;padding:2px;border-radius:3px;'>${{label}}</div>` 
                               }})
                           }});
                           layerGroup.addLayer(marker);
                       }} else {{
                           // Líneas y polígonos - convertir coordenadas correctamente
                           if (feature.geometry.type === 'LineString') {{
                               const coords = feature.geometry.coordinates.map(coord => [coord[1], coord[0]]);
                               const line = L.polyline(coords, {{
                                   color: color, 
                                   weight: 2, 
                                   opacity: 0.8
                               }});
                               layerGroup.addLayer(line);
                           }} else if (feature.geometry.type === 'Polygon') {{
                               const coords = feature.geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
                               const polygon = L.polygon(coords, {{
                                   color: color, 
                                   weight: 2, 
                                   opacity: 0.8,
                                   fillOpacity: 0.1
                               }});
                               layerGroup.addLayer(polygon);
                           }} else {{
                               // Otros tipos usando geoJSON estándar
                               const geoJsonLayer = L.geoJSON(feature, {{
                                   style: {{ color: color, weight: 2, opacity: 0.8 }}
                               }});
                               layerGroup.addLayer(geoJsonLayer);
                           }}
                       }}
            }});
            
            overlayMaps[layer] = layerGroup;
            layerGroup.addTo(map);
        }});

        // Control de capas
        L.control.layers(baseMaps, overlayMaps, {{ position: 'topright', collapsed: false }}).addTo(map);

        // Ajuste de extensión
        const bounds = {bounds_str};
        if (bounds && bounds.length === 2) {{ 
            map.fitBounds(bounds); 
        }} else {{
            try {{
                let allBounds = [];
                Object.values(overlayMaps).forEach(l => {{
                    if (l.getBounds) allBounds.push(l.getBounds());
                }});
                if (allBounds.length) {{
                    let merged = allBounds[0];
                    for (let i = 1; i < allBounds.length; i++) {{
                        merged.extend(allBounds[i]);
                    }}
                    map.fitBounds(merged);
                }} else {{
                    map.setView([0,0], 2);
                }}
            }} catch (e) {{ map.setView([0,0], 2); }}
        }}
    </script>
</body>
</html>"""
    else:
        # Modo TYPE: Agrupar por tipo (puntos, líneas, textos)
        html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title} - Map Viewer</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style> 
        html, body {{ height: 100%; margin: 0; }} 
        #map {{ height: 100vh; }} 
        .leaflet-control-layers-expanded {{ max-height: 60vh; overflow: auto; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const map = L.map('map', {{ preferCanvas: true }});
        
        // Capas base
        const calles = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: 'OpenStreetMap', maxZoom: 19 }});
        const positron = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png', {{ attribution: 'CartoDB Positron', maxZoom: 19 }});
        const satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ attribution: 'Esri', maxZoom: 19 }});
        const baseMaps = {{
            "Calles": calles,
            "Positron": positron,
            "Satelital": satelite
        }};
        
        // Agregar capa base por defecto
        positron.addTo(map);

        // GeoJSON y grupos por TIPO
        const data = {geojson_str};
        function groupByType(features) {{
            const groups = {{}};
            features.forEach(f => {{
                const type = (f.properties && f.properties.type) ? f.properties.type : 'Otro';
                if (!groups[type]) groups[type] = [];
                groups[type].push(f);
            }});
            return groups;
        }}
        
        const grouped = groupByType(data.features || []);
        const overlayMaps = {{}};
        
        Object.keys(grouped).forEach(type => {{
            const feats = grouped[type];
            let layer;
            
                   if (type === 'point' || type === 'block') {{
                       layer = L.layerGroup();
                       feats.forEach(feature => {{
                           const [lon, lat] = feature.geometry.coordinates;
                           const marker = L.circleMarker([lat, lon], {{ radius: 4, color: '#00ff00', fillOpacity: 0.8 }});
                           layer.addLayer(marker);
                       }});
                   }} else if (type === 'text') {{
                       layer = L.layerGroup();
                       feats.forEach(feature => {{
                           const [lon, lat] = feature.geometry.coordinates;
                           const label = feature.properties && feature.properties.text ? feature.properties.text : '';
                           const marker = L.marker([lat, lon], {{
                               icon: L.divIcon({{ 
                                   className: '', 
                                   html: `<div style='font-size:12px;color:#0d6efd;font-weight:600;background:white;padding:2px;border-radius:3px;'>${{label}}</div>` 
                               }})
                           }});
                           layer.addLayer(marker);
                       }});
                   }} else {{
                       // Líneas y polígonos - manejar coordenadas correctamente
                       layer = L.layerGroup();
                       feats.forEach(feature => {{
                           if (feature.geometry.type === 'LineString') {{
                               const coords = feature.geometry.coordinates.map(coord => [coord[1], coord[0]]);
                               const line = L.polyline(coords, {{ color: '#ff0000', weight: 2, opacity: 0.8 }});
                               layer.addLayer(line);
                           }} else if (feature.geometry.type === 'Polygon') {{
                               const coords = feature.geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
                               const polygon = L.polygon(coords, {{ color: '#ff0000', weight: 2, opacity: 0.8, fillOpacity: 0.1 }});
                               layer.addLayer(polygon);
                           }} else {{
                               // Otros tipos usando geoJSON estándar
                               const geoJsonLayer = L.geoJSON(feature, {{ style: {{ color: '#ff0000', weight: 2, opacity: 0.8 }} }});
                               layer.addLayer(geoJsonLayer);
                           }}
                       }});
                   }}
            
            overlayMaps[type.charAt(0).toUpperCase() + type.slice(1)] = layer;
            layer.addTo(map);
        }});

        // Control de capas
        L.control.layers(baseMaps, overlayMaps, {{ position: 'topright', collapsed: false }}).addTo(map);

        // Ajuste de extensión
        const bounds = {bounds_str};
        if (bounds && bounds.length === 2) {{ 
            map.fitBounds(bounds); 
        }} else {{
            try {{
                let allBounds = [];
                Object.values(overlayMaps).forEach(l => {{
                    if (l.getBounds) allBounds.push(l.getBounds());
                }});
                if (allBounds.length) {{
                    let merged = allBounds[0];
                    for (let i = 1; i < allBounds.length; i++) {{
                        merged.extend(allBounds[i]);
                    }}
                    map.fitBounds(merged);
                }} else {{
                    map.setView([0,0], 2);
                }}
            }} catch (e) {{ map.setView([0,0], 2); }}
        }}
    </script>
</body>
</html>"""
    
    return html_template

def create_mapbox_html(geojson_data, title="Visor GeoJSON Profesional", folder_name="Proyecto", grouping_mode="layer"):
    """Genera HTML con visor Mapbox usando el template avanzado"""
    try:
        gj_obj = json.loads(json.dumps(geojson_data))
        geojson_str = json.dumps(gj_obj, indent=2, ensure_ascii=False)
    except Exception:
        geojson_str = json.dumps(geojson_data, indent=2, ensure_ascii=False)
    
    bounds = compute_bounds_from_geojson(geojson_data)
    if bounds:
        center_lat = (bounds[0][0] + bounds[1][0]) / 2
        center_lon = (bounds[0][1] + bounds[1][1]) / 2
        mapbox_bounds = [bounds[0][1], bounds[0][0], bounds[1][1], bounds[1][0]]
    else:
        center_lat, center_lon = -2.0, -78.4
        mapbox_bounds = [-79.0, -3.0, -77.0, -1.0]
    
    mapbox_html = f'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - {folder_name}</title>
  <script src="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js"></script>
  <link href="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css" rel="stylesheet" />
  <style>
    body {{ margin: 0; padding: 0; font-family: 'Arial', sans-serif; height: 100vh; overflow: hidden; }}
    #map {{ width: 100%; height: 100%; }}
    #panel-trigger {{ position: absolute; top: 0; left: 0; width: 280px; height: 450px; z-index: 1; }}
    #floating-panel {{ position: absolute; top: 90px; left: 15px; width: 250px; background-color: rgba(40, 40, 40, 0.7); backdrop-filter: blur(5px); border-radius: 8px; padding: 15px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); z-index: 2; color: white; opacity: 0; pointer-events: none; transition: opacity 0.3s ease; max-height: 70vh; overflow-y: auto; }}
    #panel-trigger:hover #floating-panel {{ opacity: 1; pointer-events: auto; }}
    .control-group {{ margin-bottom: 15px; }}
    .control-group h3 {{ margin: 0 0 10px 0; font-size: 14px; font-weight: bold; border-bottom: 1px solid rgba(255, 255, 255, 0.2); padding-bottom: 5px; }}
    .style-select {{ width: 100%; padding: 8px; background-color: rgba(20, 20, 20, 0.9); color: white; border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 4px; margin-bottom: 15px; font-size: 12px; }}
    .elevation-input {{ width: 100%; padding: 8px; background-color: rgba(255, 255, 255, 0.1); color: white; border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 4px; font-size: 12px; }}
    .checkbox-group {{ display: flex; align-items: center; margin: 8px 0; }}
    .checkbox-group input {{ margin-right: 8px; cursor: pointer; }}
    .checkbox-group label {{ font-size: 12px; cursor: pointer; flex-grow: 1; }}
    .color-select {{ width: 70px; padding: 4px; background-color: rgba(20, 20, 20, 0.9); color: white; border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 4px; font-size: 12px; }}
    #error {{ color: #ff6b6b; font-size: 12px; margin-top: 10px; display: none; }}
    #developer-footer {{ position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%); z-index: 1; color: #ffffff; font-size: 12px; background-color: rgba(40, 40, 40, 0.5); padding: 5px 10px; border-radius: 4px; pointer-events: none; }}
    #api-modal {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.8); display: flex; justify-content: center; align-items: center; z-index: 1000; }}
    #api-modal.hidden {{ display: none; }}
    #api-modal-content {{ background-color: #333; padding: 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); color: white; width: 90%; max-width: 400px; text-align: center; }}
    #api-modal-content h2 {{ margin: 0 0 15px 0; font-size: 18px; }}
    #api-modal-content input {{ width: 100%; padding: 8px; margin-bottom: 15px; background-color: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 4px; color: white; font-size: 14px; }}
    #api-modal-content button {{ padding: 8px 16px; background-color: #007bff; border: none; border-radius: 4px; color: white; font-size: 14px; cursor: pointer; transition: background-color 0.3s ease; }}
    #api-modal-content button:hover {{ background-color: #0056b3; }}
    #api-error {{ color: #ff6b6b; font-size: 12px; margin-top: 10px; display: none; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="api-modal" class="hidden">
    <div id="api-modal-content">
      <h2>Ingrese su Mapbox API Key</h2>
      <input type="text" id="api-key-input" placeholder="pk.eyJ1IjoieW91ci11c2Vybm..." />
      <button id="api-submit">Confirmar</button>
      <div id="api-error">Por favor, ingrese una clave válida</div>
    </div>
  </div>
  <div id="panel-trigger">
    <div id="floating-panel">
      <div class="control-group">
        <h3>ESTILO DEL MAPA</h3>
        <select id="styleSelect" class="style-select">
          <option value="mapbox://styles/mapbox/satellite-streets-v12" selected>Satélite Calles</option>
          <option value="mapbox://styles/mapbox/satellite-v9">Satélite Solu</option>
          <option value="mapbox://styles/mapbox/light-v11">Claro</option>
          <option value="mapbox://styles/mapbox/dark-v11">Oscuro</option>
          <option value="mapbox://styles/mapbox/outdoors-v12">Outdoors</option>
        </select>
      </div>
      <div class="control-group">
        <h3>FACTOR DE ELEVACIÓN (3D)</h3>
        <input type="number" id="elevationFactor" class="elevation-input" value="1.5" min="0" max="10" step="0.1" placeholder="Factor de elevación (0-10)" />
      </div>
      <div class="control-group">
        <h3>LAYERS DEL MAPA</h3>
        <div id="layers-control"></div>
      </div>
      <div id="error"></div>
    </div>
  </div>
  <div id="developer-footer">Desarrollador: Patricio Sarmiento Reinoso</div>
  <script>
    const mapboxTokenFromPython = "{get_mapbox_token() or ''}";
    const rawGeoJSON = {geojson_str};
    
    // Función defensiva para corregir coordenadas (Ecuador focus)
    function fixCoord(c) {{
        if (!c || c.length < 2) return c;
        let c0 = c[0], c1 = c[1];
        // Heurística: Si abs(c0) < 20 (lat) y abs(c1) > 50 (lon), estaban trocadas para GeoJSON
        if (Math.abs(c0) < 20 && Math.abs(c1) > 50) {{
            return [c1, c0]; // c1 es lon, c0 es lat -> [lon, lat]
        }}
        return c;
    }}

    function fixGeom(g) {{
        if (!g || !g.coordinates) return g;
        if (g.type === 'Point') g.coordinates = fixCoord(g.coordinates);
        else if (g.type === 'LineString' || g.type === 'MultiPoint') g.coordinates = g.coordinates.map(fixCoord);
        else if (g.type === 'Polygon' || g.type === 'MultiLineString') g.coordinates = g.coordinates.map(r => r.map(fixCoord));
        else if (g.type === 'MultiPolygon') g.coordinates = g.coordinates.map(p => p.map(r => r.map(fixCoord)));
        return g;
    }}

    // Aplicar corrección a todo el GeoJSON
    if (rawGeoJSON.features) {{
        rawGeoJSON.features.forEach(f => {{ f.geometry = fixGeom(f.geometry); }});
    }}

    let mapboxAccessToken = mapboxTokenFromPython || localStorage.getItem('mapboxAccessToken');
    const apiModal = document.getElementById('api-modal');
    const apiKeyInput = document.getElementById('api-key-input');
    const apiSubmitButton = document.getElementById('api-submit');
    const apiError = document.getElementById('api-error');
    let map = null;
    let currentGeoJSON = rawGeoJSON;
    let layersList = [];
    let layerColors = {{}};

    function initializeMap() {{
      try {{
        mapboxgl.accessToken = mapboxAccessToken;
        const initialCenter = [{center_lon}, {center_lat}];
        map = new mapboxgl.Map({{ 
          container: 'map',
          style: 'mapbox://styles/mapbox/satellite-streets-v12',
          center: initialCenter,
          zoom: 14,
          pitch: 45,
          bearing: -17.6,
          maxZoom: 22
        }});
        map.addControl(new mapboxgl.NavigationControl());
        map.addControl(new mapboxgl.FullscreenControl());
        map.on('load', function() {{
          applyElevationFactor();
          loadDataToMap();
        }});

        function applyElevationFactor() {{
          const elevationFactor = parseFloat(document.getElementById('elevationFactor').value) || 1.5;
          if (!map.getSource('mapbox-dem')) {{
            map.addSource('mapbox-dem', {{ type: 'raster-dem', url: 'mapbox://mapbox.terrain-rgb', tileSize: 512, maxzoom: 14 }});
          }}
          map.setTerrain({{ source: 'mapbox-dem', exaggeration: elevationFactor }});
        }}

        function zoomToData() {{
          const bounds = new mapboxgl.LngLatBounds();
          let hasVal = false;
          currentGeoJSON.features.forEach(f => {{
              if (f.geometry && f.geometry.coordinates) {{
                  const coords = f.geometry.coordinates;
                  if (f.geometry.type === 'Point') {{ bounds.extend(coords); hasVal = true; }}
                  else if (f.geometry.type === 'LineString') {{ coords.forEach(c => bounds.extend(c)); hasVal = true; }}
                  else if (f.geometry.type === 'Polygon') {{ coords[0].forEach(c => bounds.extend(c)); hasVal = true; }}
              }}
          }});
          if (hasVal) map.fitBounds(bounds, {{ padding: 50, duration: 2000 }});
        }}

        function loadDataToMap() {{
          const layers = {{}};
          currentGeoJSON.features.forEach(f => {{
              const l = f.properties.layer || 'Defecto';
              if (!layers[l]) layers[l] = [];
              layers[l].push(f);
          }});
          layersList = Object.keys(layers);
          const control = document.getElementById('layers-control');
          control.innerHTML = '';
          layersList.forEach(l => {{
              layerColors[l] = layerColors[l] || '#ff0000';
              const div = document.createElement('div');
              div.className = 'checkbox-group';
              div.innerHTML = `<input type="checkbox" id="sh-${{l}}" checked><label for="sh-${{l}}">${{l}}</label><input type="color" value="${{layerColors[l]}}" id="cl-${{l}}" class="color-select">`;
              control.appendChild(div);
              div.querySelector('input[type="checkbox"]').onchange = loadLayers;
              div.querySelector('input[type="color"]').onchange = (e) => {{ layerColors[l] = e.target.value; loadLayers(); }};
          }});
          loadLayers();
          setTimeout(zoomToData, 500);
        }}

        function loadLayers() {{
          layersList.forEach(l => {{
              ['pts','lns','txt'].forEach(s => {{ if (map.getLayer(`${{l}}-${{s}}`)) map.removeLayer(`${{l}}-${{s}}`); }});
          }});
          if (!map.getSource('src')) map.addSource('src', {{ type: 'geojson', data: currentGeoJSON }});
          else map.getSource('src').setData(currentGeoJSON);

          layersList.forEach(l => {{
              if (!document.getElementById(`sh-${{l}}`).checked) return;
              const col = layerColors[l];
              map.addLayer({{ id: `${{l}}-pts`, type: 'circle', source: 'src', filter: ['all', ['==', ['get','layer'], l], ['in', ['get','type'], ['literal', ['point','block']]]], paint: {{ 'circle-color': col, 'circle-radius': 5 }} }});
              map.addLayer({{ id: `${{l}}-lns`, type: 'line', source: 'src', filter: ['all', ['==', ['get','layer'], l], ['in', ['get','type'], ['literal', ['line','polyline','polygon','shape']]]], paint: {{ 'line-color': col, 'line-width': 2 }} }});
              map.addLayer({{ id: `${{l}}-txt`, type: 'symbol', source: 'src', filter: ['all', ['==', ['get','layer'], l], ['==', ['get','type'], 'text']], layout: {{ 'text-field': ['get','text'], 'text-size': 12, 'text-anchor': 'top' }}, paint: {{ 'text-color': col, 'text-halo-color': '#fff', 'text-halo-width': 1 }} }});
          }});
        }}

        document.getElementById('styleSelect').onchange = (e) => {{ map.setStyle(e.target.value); map.on('style.load', () => {{ applyElevationFactor(); loadLayers(); }}); }};
        document.getElementById('elevationFactor').onchange = applyElevationFactor;
      }} catch (e) {{ console.error(e); }}
    }}

    if (mapboxAccessToken && mapboxAccessToken.startsWith('pk.')) {{ 
        initializeMap(); 
    }} else {{
      apiModal.classList.remove('hidden');
      apiSubmitButton.onclick = () => {{
        const key = apiKeyInput.value.trim();
        if (key.startsWith('pk.')) {{ 
            localStorage.setItem('mapboxAccessToken', key); 
            mapboxAccessToken = key; 
            apiModal.classList.add('hidden'); 
            initializeMap(); 
        }} else {{
            apiError.style.display = 'block';
        }}
      }};
    }}
  </script>
</body>
</html>'''
    return mapbox_html

def create_leaflet_grouped_html(geojson_data, title="Visor GeoJSON Profesional", grouping_mode="type", point_color="#ff0000", line_color="#0000ff", line_width=2):
    """Genera HTML con Leaflet y control de capas agrupadas por 'type' o 'layer'."""
    try:
        gj_obj = json.loads(json.dumps(geojson_data))
        if isinstance(gj_obj, dict) and gj_obj.get("type") == "FeatureCollection":
            for f in gj_obj.get("features", []):
                if not isinstance(f, dict): continue
                props = f.setdefault("properties", {})
                if "type" in props and isinstance(props["type"], str):
                    props["type"] = props["type"].lower()
                if "layer" not in props:
                    props["layer"] = "default"
        geojson_str = json.dumps(gj_obj, ensure_ascii=False)
    except Exception:
        geojson_str = json.dumps(geojson_data, ensure_ascii=False)

    group_key_js = "(f.properties && f.properties.layer) ? String(f.properties.layer) : 'SinGrupo'" if str(grouping_mode).lower() == "layer" else "(f.properties && f.properties.type) ? String(f.properties.type) : 'SinGrupo'"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style> 
    html, body {{ height: 100%; margin: 0; background: #f8f9fa; }} 
    #map {{ height: 100vh; width: 100%; }} 
    .leaflet-control-layers-expanded {{ max-height: 65vh; overflow-y: auto; background: rgba(255,255,255,0.9) !important; padding: 10px; border-radius: 8px; }} 
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = L.map('map', {{ preferCanvas: true }});
    const calles = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '&copy; OpenStreetMap' }});
    const satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ attribution: '&copy; Esri' }});
    const positron = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{ attribution: '&copy; CartoDB' }});
    
    const baseLayers = {{ "Calles": calles, "Satelital": satelite, "Positron": positron }};
    satelite.addTo(map);

    const data = {geojson_str};
    
    // Configuración de Estilos Dinámicos
    const pointColor = '{point_color}';
    const lineColor = '{line_color}';
    const lineWidth = {line_width};

    // Función defensiva para corregir coordenadas
    function fixCoord(c) {{
        if (!c || c.length < 2) return null;
        let lon = c[0], lat = c[1];
        if (Math.abs(lat) > 90 && Math.abs(lon) <= 90) {{
            return [lon, lat];
        }}
        return [lat, lon];
    }}

    const grouped = {{}};
    if (data && data.features) {{
      data.features.forEach(f => {{
        const key = {group_key_js};
        if (!grouped[key]) grouped[key] = L.featureGroup();
        
        const type = (f.properties && f.properties.type) ? f.properties.type.toLowerCase() : '';
        const coords = f.geometry.coordinates;

        if (type === 'text') {{
            const ll = fixCoord(coords);
            if (ll) {{
                const label = (f.properties && f.properties.text) ? String(f.properties.text) : '';
                L.marker(ll, {{ icon: L.divIcon({{ className: '', html: `<div style='font-size:11px;color:${{pointColor}};font-weight:700;background:rgba(255,255,255,0.8);border:1px solid ${{pointColor}};padding:1px 3px;border-radius:2px;white-space:nowrap;'>${{label}}</div>` }}) }}).addTo(grouped[key]);
            }}
        }} else if (f.geometry.type === 'Point') {{
            const ll = fixCoord(coords);
            if (ll) {{
                L.circleMarker(ll, {{ radius: 4, color: pointColor, weight: 1, fillOpacity: 0.8, fillColor: pointColor }}).addTo(grouped[key]);
            }}
        }} else if (f.geometry.type === 'LineString') {{
            const path = coords.map(c => fixCoord(c)).filter(c => c !== null);
            if (path.length > 1) {{
                L.polyline(path, {{ color: lineColor, weight: lineWidth, opacity: 0.9 }}).addTo(grouped[key]);
            }}
        }} else if (f.geometry.type === 'Polygon') {{
            const rings = coords.map(ring => ring.map(c => fixCoord(c)).filter(c => c !== null));
            L.polygon(rings, {{ color: lineColor, weight: lineWidth, fillOpacity: 0.3, fillColor: lineColor }}).addTo(grouped[key]);
        }}
      }});
    }}

    const overlayMaps = {{}};
    Object.keys(grouped).forEach(k => {{
        overlayMaps[k] = grouped[k];
        grouped[k].addTo(map);
    }});

    L.control.layers(baseLayers, overlayMaps, {{ position: 'topright', collapsed: false }}).addTo(map);

    const totalGroup = L.featureGroup(Object.values(grouped));
    try {{
        const bounds = totalGroup.getBounds();
        if (bounds.isValid()) {{
            map.fitBounds(bounds, {{ padding: [30, 30] }});
        }} else {{
            map.setView([0,0], 2);
        }}
    }} catch(e) {{ map.setView([0,0], 2); }}
  </script>
</body>
</html>"""
    return html

def render_map(geojson_data, group_by: str = "type"):
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
                if b: all_bounds.extend(b)
            except Exception:
                pass
        if all_bounds:
            m.fit_bounds(all_bounds)
    except Exception:
        pass

    folium.LayerControl(position="topright").add_to(m)
    st_folium(m, width=None, height=650)
