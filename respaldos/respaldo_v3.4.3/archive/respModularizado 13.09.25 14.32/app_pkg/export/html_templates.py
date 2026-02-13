import json
from typing import Any, Dict


def create_mapbox_html(geojson_data: Dict[str, Any], title: str = "Visor GeoJSON Profesional", folder_name: str = "Proyecto", grouping_mode: str = "layer") -> str:
    geojson_str = json.dumps(geojson_data, indent=2, ensure_ascii=False)
    mapbox_html = f'''
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
  <div id="api-modal">
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
          <option value="mapbox://styles/mapbox/light-v11" selected>Positron (no labels)</option>
          <option value="mapbox://styles/mapbox/satellite-v9">Satélite</option>
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
    const embeddedGeoJSON = {geojson_str};
    let mapboxAccessToken = localStorage.getItem('mapboxAccessToken');
    const apiModal = document.getElementById('api-modal');
    const apiKeyInput = document.getElementById('api-key-input');
    const apiSubmitButton = document.getElementById('api-submit');
    const apiError = document.getElementById('api-error');
    let map = null; let currentGeoJSON = embeddedGeoJSON; let layersList = []; let layerColors = {};
    function initializeMap() {
      try {
        mapboxgl.accessToken = mapboxAccessToken;
        map = new mapboxgl.Map({ container: 'map', style: 'mapbox://styles/mapbox/light-v11', center: [-78.421, -2.974], zoom: 12, pitch: 45, bearing: -17.6, maxZoom: 20 });
        map.addControl(new mapboxgl.NavigationControl());
        map.addControl(new mapboxgl.FullscreenControl());
        map.on('load', function() { applyElevationFactor(); loadDataToMap(); });
        function applyElevationFactor() {
          const elevationFactor = parseFloat(document.getElementById('elevationFactor').value) || 1.5;
          if (elevationFactor < 0 || elevationFactor > 10) { return; }
          if (!map.getSource('mapbox-dem')) {
            map.addSource('mapbox-dem', { type: 'raster-dem', url: 'mapbox://mapbox.terrain-rgb', tileSize: 512, maxzoom: 14 });
          }
          map.setTerrain({ source: 'mapbox-dem', exaggeration: elevationFactor });
          map.setPitch(45);
        }
        function zoomToData() {
          if (!currentGeoJSON) return; const bounds = new mapboxgl.LngLatBounds();
          currentGeoJSON.features.forEach(feature => {
            if (feature.geometry.type === 'Point') { bounds.extend(feature.geometry.coordinates); }
            else if (feature.geometry.type === 'LineString') { feature.geometry.coordinates.forEach(coord => { bounds.extend(coord); }); }
            else if (feature.geometry.type === 'Polygon') { feature.geometry.coordinates[0].forEach(coord => { bounds.extend(coord); }); }
          });
          if (!bounds.isEmpty()) { map.fitBounds(bounds, { padding: 50, maxZoom: 18, duration: 1500 }); }
        }
        function loadDataToMap() {
          if (!currentGeoJSON) return; const groupingMode = '{grouping_mode}';
          const typeMapping = { 'point': '📍 Puntos', 'line': '📏 Líneas', 'polyline': '🔗 Polilíneas', 'circle': '⭕ Círculos', 'text': '📝 Textos', 'block': '🔲 Bloques', 'shape': '🔸 Formas', 'track': '🛤️ Tracks', 'route': '🗺️ Rutas' };
          if (groupingMode === 'type') { layersList = [...new Set(currentGeoJSON.features.map(feature => { const type = feature.properties.type || 'default'; return typeMapping[type] || type; }))]; }
          else { layersList = [...new Set(currentGeoJSON.features.map(feature => feature.properties.layer || 'default'))]; }
          layersList.sort();
          layersList.forEach(layer => { if (!layerColors[layer]) { const defaultColors = ['#00ff00', '#0000ff', '#ff0000', '#ffff00', '#ffffff', '#00ffff']; layerColors[layer] = defaultColors[Object.keys(layerColors).length % defaultColors.length]; }});
          const layersControlDiv = document.getElementById('layers-control'); layersControlDiv.innerHTML = '';
          layersList.forEach(layer => {
            const layerDiv = document.createElement('div'); layerDiv.className = 'checkbox-group';
            const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.id = `show-${layer}`; checkbox.checked = true; checkbox.addEventListener('change', () => { loadLayers(); });
            const label = document.createElement('label'); label.htmlFor = `show-${layer}`; label.textContent = layer;
            const colorSelect = document.createElement('select'); colorSelect.id = `color-${layer}`; colorSelect.className = 'color-select';
            const colorOptions = [ { value: '#00ff00', text: 'Verde' }, { value: '#ff0000', text: 'Rojo' }, { value: '#0000ff', text: 'Azul' }, { value: '#ffff00', text: 'Amarillo' }, { value: '#ffffff', text: 'Blanco' }, { value: '#000000', text: 'Negro' } ];
            colorOptions.forEach(option => { const opt = document.createElement('option'); opt.value = option.value; opt.textContent = option.text; if (option.value === layerColors[layer]) { opt.selected = true; } colorSelect.appendChild(opt); });
            colorSelect.addEventListener('change', () => { layerColors[layer] = colorSelect.value; loadLayers(); });
            layerDiv.appendChild(checkbox); layerDiv.appendChild(label); layerDiv.appendChild(colorSelect); layersControlDiv.appendChild(layerDiv);
          });
          loadLayers(); zoomToData();
        }
        function loadLayers() {
          const existingLayerIds = map.getStyle().layers.map(l => l.id);
          existingLayerIds.forEach(id => { if (id.startsWith('custom-')) { map.removeLayer(id); } });
          if (!map.getSource('geojson-data')) { map.addSource('geojson-data', { type: 'geojson', data: currentGeoJSON }); } else { map.getSource('geojson-data').setData(currentGeoJSON); }
          const groupingMode = '{grouping_mode}';
          const typeMap = { '📍 Puntos': 'point', '📏 Líneas': 'line', '🔗 Polilíneas': 'polyline', '⭕ Círculos': 'circle', '📝 Textos': 'text', '🔲 Bloques': 'block', '🔸 Formas': 'shape', '🛤️ Tracks': 'track', '🗺️ Rutas': 'route' };
          layersList.forEach(layer => {
            const showLayer = document.getElementById(`show-${layer}`).checked; if (!showLayer) return;
            let filter; if (groupingMode === 'type') { const realType = typeMap[layer] || layer; filter = ['==', ['get', 'type'], realType]; } else { filter = ['==', ['get', 'layer'], layer]; }
            map.addLayer({ id: `custom-${layer}-lines`, type: 'line', source: 'geojson-data', filter: ['all', filter, ['in', '$geometryType', 'LineString', 'Polygon']], paint: { 'line-color': layerColors[layer] || '#0000ff', 'line-width': 3, 'line-opacity': 0.8 }});
            map.addLayer({ id: `custom-${layer}-points`, type: 'circle', source: 'geojson-data', filter: ['all', filter, ['==', '$geometryType', 'Point']], paint: { 'circle-radius': 6, 'circle-color': layerColors[layer] || '#00ff00', 'circle-opacity': 0.8 }});
            map.addLayer({ id: `custom-${layer}-circles`, type: 'fill', source: 'geojson-data', filter: ['all', filter, ['==', ['get', 'type'], 'circle']], paint: { 'fill-color': layerColors[layer] || '#ff0000', 'fill-opacity': 0.5 }});
            map.addLayer({ id: `custom-${layer}-labels`, type: 'symbol', source: 'geojson-data', filter: ['all', filter, ['==', ['get', 'type'], 'text']], layout: { 'text-field': ['get', 'text'], 'text-size': 12, 'text-anchor': 'top', 'text-offset': [0, 1] }, paint: { 'text-color': layerColors[layer] || '#ffffff', 'text-halo-color': '#000000', 'text-halo-width': 1 }});
          });
        }
        document.getElementById('styleSelect').addEventListener('change', function() { const selectedStyle = this.value; map.setStyle(selectedStyle); map.once('style.load', function() { applyElevationFactor(); loadDataToMap(); }); });
        document.getElementById('elevationFactor').addEventListener('change', function() { applyElevationFactor(); });
      } catch (error) {
        console.error('Error inicializando el mapa:', error);
        const err = document.getElementById('error'); if (err) { err.textContent = 'Error inicializando el mapa: ' + error.message; err.style.display = 'block'; }
      }
    }
    if (mapboxAccessToken && mapboxAccessToken.startsWith('pk.')) { apiModal.classList.add('hidden'); initializeMap(); }
    else {
      apiModal.classList.remove('hidden');
      apiSubmitButton.addEventListener('click', function() {
        const apiKey = apiKeyInput.value.trim();
        if (apiKey === '' || !apiKey.startsWith('pk.')) { const err = document.getElementById('api-error'); err.textContent = 'Por favor, ingrese una clave válida que comience con pk.'; err.style.display = 'block'; return; }
        localStorage.setItem('mapboxAccessToken', apiKey); mapboxAccessToken = apiKey; apiModal.classList.add('hidden'); initializeMap();
      });
      apiKeyInput.addEventListener('keypress', function(e) { if (e.key === 'Enter') { apiSubmitButton.click(); } });
    }
  </script>
</body>
</html>'''
    return mapbox_html


leaf_tpl = (
    """<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>__TITLE__</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" />
  <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script>
  <style> html, body { height: 100%; margin: 0; } #map { height: 100vh; } </style>
</head>
<body>
  <div id=\"map\"></div>
  <script>
    const map = L.map('map', { preferCanvas: true });
    const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors' });
    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: '© Esri' });
    const positron = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { attribution: '© CartoDB', subdomains: 'abcd', maxZoom: 19 });
    positron.addTo(map);
    const baseLayers = { 'Positron': positron, 'OpenStreetMap': osm, 'Satélite': satellite };
    const geojsonData = __GEOJSON__;
    const pointsGroup = L.layerGroup();
    const linesGroup = L.layerGroup();
    if (geojsonData && geojsonData.features) {
      geojsonData.features.forEach((feature, index) => {
        if (feature.geometry.type === 'Point') {
          const [lon, lat] = feature.geometry.coordinates;
          const props = feature.properties;
          const marker = L.circleMarker([lat, lon], { radius: 8, fillColor: '#ff7800', color: '#000', weight: 1, opacity: 1, fillOpacity: 0.8 });
          let popupContent = '<b>Punto ' + (props.No || 'N/A') + '</b><br/>';
          popupContent += 'Cota: ' + (props.cota || '0') + '<br/>';
          if (props.desc && props.desc !== 'nan' && props.desc !== '') { popupContent += 'Desc: ' + props.desc; }
          marker.bindPopup(popupContent);
          pointsGroup.addLayer(marker);
        } else if (feature.geometry.type === 'LineString') {
          const coords = feature.geometry.coordinates.map(coord => [coord[1], coord[0]]);
          const line = L.polyline(coords, { color: '#ff0000', weight: 3, opacity: 0.8, dashArray: null });
          line.bindPopup('<b>Polígono ' + (index + 1) + '</b><br/>Puntos: ' + coords.length);
          linesGroup.addLayer(line);
        }
      });
    }
    pointsGroup.addTo(map);
    linesGroup.addTo(map);
    const overlayMaps = { 'Puntos': pointsGroup, 'Líneas': linesGroup };
    L.control.layers(baseLayers, overlayMaps).addTo(map);
    try {
      const bounds = __BOUNDS__;
      map.fitBounds([[bounds[0][0], bounds[0][1]], [bounds[1][0], bounds[1][1]]], {padding: [20, 20]});
    } catch(e) {
      map.setView([__CENTER_LAT__, __CENTER_LON__], 15);
    }
  </script>
</body>
</html>
"""
)


__all__ = [
    "create_mapbox_html",
    "leaf_tpl",
]
