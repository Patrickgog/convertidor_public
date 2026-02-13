import numpy as np
import scipy.interpolate as interp
from scipy.interpolate import griddata
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS
import tempfile
import os
import time
import pandas as pd
import streamlit as st

def validate_heatmap_data(points_df):
    """Valida los datos para el mapa de calor y proporciona información de debug."""
    if points_df is None or len(points_df) == 0:
        return {"valid": False, "message": "No hay datos para procesar"}
    if len(points_df) < 3:
        return {"valid": False, "message": "Se necesitan al menos 3 puntos para generar el mapa de calor"}
    required_cols = ['x', 'y', 'cota']
    missing_cols = [col for col in required_cols if col not in points_df.columns]
    if missing_cols:
        return {"valid": False, "message": f"Faltan columnas requeridas: {missing_cols}"}
    stats = {
        "valid": True,
        "total_points": len(points_df),
        "x_range": (points_df['x'].min(), points_df['x'].max()),
        "y_range": (points_df['y'].min(), points_df['y'].max()),
        "z_range": (points_df['cota'].min(), points_df['cota'].max()),
        "area_coverage": (points_df['x'].max() - points_df['x'].min()) * (points_df['y'].max() - points_df['y'].min()),
        "center": ((points_df['x'].min() + points_df['x'].max()) / 2, (points_df['y'].min() + points_df['y'].max()) / 2)
    }
    return stats

def calculate_raster_bounds(points_df, margin_percent=10):
    """Calcula los bounds del raster basado en los puntos topográficos."""
    if points_df is None or len(points_df) == 0:
        return None
    min_x, max_x = points_df['x'].min(), points_df['x'].max()
    min_y, max_y = points_df['y'].min(), points_df['y'].max()
    x_range = max_x - min_x
    y_range = max_y - min_y
    margin_x = x_range * (margin_percent / 100)
    margin_y = y_range * (margin_percent / 100)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    max_range = max(x_range, y_range)
    half_size = (max_range + max(margin_x, margin_y)) / 2
    return (center_x - half_size, center_y - half_size, center_x + half_size, center_y + half_size)

def debug_heatmap_coordinates(points_df, bounds, resolution):
    min_x, min_y, max_x, max_y = bounds
    pixel_width = (max_x - min_x) / resolution
    pixel_height = (max_y - min_y) / resolution
    transform = Affine.translation(min_x, min_y) * Affine.scale(pixel_width, pixel_height)
    corners = {
        "bottom_left": transform * (0, 0),
        "bottom_right": transform * (resolution, 0),
        "top_left": transform * (0, resolution),
        "top_right": transform * (resolution, resolution)
    }
    return {
        "bounds": bounds,
        "resolution": resolution,
        "pixel_size": (pixel_width, pixel_height),
        "transform_matrix": [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f],
        "corners": corners,
        "points_sample": {
            "first_point": (points_df['x'].iloc[0], points_df['y'].iloc[0]) if len(points_df) > 0 else None,
            "last_point": (points_df['x'].iloc[-1], points_df['y'].iloc[-1]) if len(points_df) > 0 else None,
            "center": ((points_df['x'].min() + points_df['x'].max()) / 2, (points_df['y'].min() + points_df['y'].max()) / 2)
        }
    }

def create_heatmap_debug_file(points_df, bounds, resolution, output_path):
    try:
        debug_info = debug_heatmap_coordinates(points_df, bounds, resolution)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== DEBUG MAPA DE CALOR ===\n\n")
            f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("=== BOUNDS ===\n")
            f.write(f"Min X: {bounds[0]:.6f}\nMin Y: {bounds[1]:.6f}\nMax X: {bounds[2]:.6f}\nMax Y: {bounds[3]:.6f}\n\n")
            f.write("=== RESOLUCIÓN ===\n")
            f.write(f"Resolución: {resolution}x{resolution}\nTamaño de píxel X: {debug_info['pixel_size'][0]:.6f}\nTamaño de píxel Y: {debug_info['pixel_size'][1]:.6f}\n\n")
            f.write("=== MATRIZ DE TRANSFORMACIÓN ===\n")
            m = debug_info['transform_matrix']
            f.write(f"a={m[0]:.6f}, b={m[1]:.6f}\nc={m[2]:.6f}, d={m[3]:.6f}\ne={m[4]:.6f}, f={m[5]:.6f}\n\n")
            f.write("=== ESQUINAS DEL RASTER ===\n")
            c = debug_info['corners']
            f.write(f"Top Left: {c['top_left']}\nTop Right: {c['top_right']}\nBottom Left: {c['bottom_left']}\nBottom Right: {c['bottom_right']}\n\n")
            f.write("=== PUNTOS DE MUESTRA ===\n")
            p = debug_info['points_sample']
            f.write(f"Primero: {p['first_point']}\nÚltimo: {p['last_point']}\nCentro: {p['center']}\n\n")
            f.write("=== TODOS LOS PUNTOS ===\n")
            for i, row in points_df.iterrows():
                f.write(f"P{i+1}: X={row['x']:.6f}, Y={row['y']:.6f}, Z={row['cota']:.6f}\n")
        return True
    except Exception as e:
        st.error(f"Error al crear archivo de debug: {e}")
        return False

def create_sample_heatmap_data():
    sample_points = [
        [200000, 9800000, 2450], [200100, 9800000, 2445], [200200, 9800000, 2440],
        [200000, 9800100, 2455], [200100, 9800100, 2450], [200200, 9800100, 2445],
        [200050, 9800050, 2448], [200150, 9800050, 2443], [200250, 9800050, 2438],
        [200075, 9800075, 2446],
    ]
    return pd.DataFrame(sample_points, columns=['x', 'y', 'cota'])

def get_crs_options():
    return {
        'EPSG:32719': 'UTM Zona 19S (Ecuador, Perú)',
        'EPSG:32718': 'UTM Zona 18S (Ecuador, Perú)',
        'EPSG:32717': 'UTM Zona 17S (Ecuador, Perú)',
        'EPSG:32619': 'UTM Zona 19N (Colombia, Venezuela)',
        'EPSG:32618': 'UTM Zona 18N (Colombia, Venezuela)',
        'EPSG:4326': 'WGS84 (Lat/Lon)',
        'EPSG:3857': 'Web Mercator (Google Maps)',
        'EPSG:3116': 'MAGNA-SIRGAS / Colombia Bogota zone',
        'EPSG:3117': 'MAGNA-SIRGAS / Colombia East zone',
        'EPSG:3118': 'MAGNA-SIRGAS / Colombia West zone',
    }

def create_heatmap_geotiff_point_perfect(points_list, crs_code='EPSG:32717', resolution=100, padding_percent=1.0, method='cubic'):
    if not points_list or len(points_list) < 3:
        st.error("❌ Se requieren al menos 3 puntos")
        return None
    try:
        points_array = np.array(points_list)
        x_coords, y_coords, z_values = points_array[:, 0], points_array[:, 1], points_array[:, 2]
        min_x, max_x = np.min(x_coords), np.max(x_coords)
        min_y, max_y = np.min(y_coords), np.max(y_coords)
        x_range, y_range = max_x - min_x, max_y - min_y
        padding_x, padding_y = (x_range * padding_percent) / 100.0, (y_range * padding_percent) / 100.0
        bounds_min_x, bounds_max_x = min_x - padding_x, max_x + padding_x
        bounds_min_y, bounds_max_y = min_y - padding_y, max_y + padding_y
        x_grid = np.linspace(bounds_min_x, bounds_max_x, resolution)
        y_grid = np.linspace(bounds_min_y, bounds_max_y, resolution)
        X_grid, Y_grid = np.meshgrid(x_grid, y_grid, indexing='xy')
        grid_points, grid_values = [], []
        for x, y, z in points_list:
            xi, yi = np.argmin(np.abs(x_grid - x)), np.argmin(np.abs(y_grid - y))
            grid_points.append([x_grid[xi], y_grid[yi]])
            grid_values.append(z)
        Z_interpolated = interp.griddata(np.array(grid_points), np.array(grid_values), (X_grid, Y_grid), method=method, fill_value=np.nan)
        valid_data = Z_interpolated[~np.isnan(Z_interpolated)]
        if len(valid_data) > 0:
            min_val, max_val, mean_val, std_val = float(np.min(valid_data)), float(np.max(valid_data)), float(np.mean(valid_data)), float(np.std(valid_data))
        else:
            original_z_values = np.array([p[2] for p in points_list])
            min_val, max_val, mean_val, std_val = float(np.min(original_z_values)), float(np.max(original_z_values)), float(np.mean(original_z_values)), float(np.std(original_z_values))
            Z_interpolated = np.full((resolution, resolution), np.nan)
            for x, y, z in points_list: Z_interpolated[np.argmin(np.abs(y_grid - y)), np.argmin(np.abs(x_grid - x))] = z
        Z_interpolated = np.flipud(Z_interpolated)
        pixel_width, pixel_height = (bounds_max_x - bounds_min_x) / resolution, (bounds_max_y - bounds_min_y) / resolution
        transform = Affine.translation(bounds_min_x, bounds_max_y) * Affine.scale(pixel_width, -pixel_height)
        epsg = int(crs_code.split(':')[1]) if crs_code.startswith('EPSG:') else None
        crs = CRS.from_epsg(epsg) if epsg else CRS.from_string(crs_code)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            tmp_path = tmp.name
        with rasterio.open(tmp_path, 'w', driver='GTiff', height=resolution, width=resolution, count=1, dtype=rasterio.float32, crs=crs, transform=transform, nodata=np.nan, compress='lzw', tiled=True, blockxsize=256, blockysize=256, interleave='band', photometric='minisblack') as dst:
            dst.write(Z_interpolated.astype(rasterio.float32), 1)
            dst.update_tags(STATISTICS_MINIMUM=min_val, STATISTICS_MAXIMUM=max_val, STATISTICS_MEAN=mean_val, STATISTICS_STDDEV=std_val)
            dst.update_tags(SOFTWARE="Antigravity Heatmap", DATETIME=time.strftime("%Y:%m:%d %H:%M:%S"))
        with open(tmp_path, 'rb') as f: data = f.read()
        os.unlink(tmp_path)
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def create_heatmap_geotiff_precise(points_list, crs_code='EPSG:32717', resolution=100, padding_percent=1.0, method='cubic'):
    if not points_list or len(points_list) < 3:
        st.error("❌ Se requieren al menos 3 puntos")
        return None
    try:
        arr = np.array(points_list)
        x_coords, y_coords, z_values = arr[:, 0], arr[:, 1], arr[:, 2]
        min_x, max_x = np.min(x_coords), np.max(x_coords)
        min_y, max_y = np.min(y_coords), np.max(y_coords)
        xr, yr = max_x - min_x, max_y - min_y
        px, py = (xr * padding_percent) / 100.0, (yr * padding_percent) / 100.0
        bx_min, bx_max, by_min, by_max = min_x - px, max_x + px, min_y - py, max_y + py
        x_grid, y_grid = np.linspace(bx_min, bx_max, resolution), np.linspace(by_min, by_max, resolution)
        XG, YG = np.meshgrid(x_grid, y_grid, indexing='ij')
        Z_int = interp.griddata(np.column_stack((x_coords, y_coords)), z_values, (XG, YG), method=method, fill_value=np.nan)
        Z_int = np.flipud(Z_int)
        pw, ph = (bx_max - bx_min) / resolution, (by_max - by_min) / resolution
        transform = Affine.translation(bx_min, by_max) * Affine.scale(pw, -ph)
        crs = CRS.from_epsg(int(crs_code.split(':')[1])) if crs_code.startswith('EPSG:') else CRS.from_string(crs_code)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            tmp_path = tmp.name
        with rasterio.open(tmp_path, 'w', driver='GTiff', height=resolution, width=resolution, count=1, dtype=rasterio.float32, crs=crs, transform=transform, nodata=np.nan, compress='lzw', tiled=True) as dst:
            dst.write(Z_int.astype(rasterio.float32), 1)
        with open(tmp_path, 'rb') as f: data = f.read()
        os.unlink(tmp_path)
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def create_heatmap_geotiff_corrected(points_df, bounds, resolution=500, method='linear', crs_code='EPSG:32719'):
    if points_df is None or len(points_df) < 3: return None
    try:
        x_coords, y_coords, z_values = points_df['x'].values, points_df['y'].values, points_df['cota'].values
        min_x, min_y, max_x, max_y = bounds
        res = max(resolution, 100)
        xg, yg = np.linspace(min_x, max_x, res), np.linspace(min_y, max_y, res)
        XG, YG = np.meshgrid(xg, yg, indexing='ij')
        Z_int = griddata(np.column_stack((x_coords, y_coords)), z_values, (XG, YG), method='cubic' if method == 'linear' and len(points_df) > 10 else method, fill_value=np.nan)
        pw, ph = (max_x - min_x) / res, (max_y - min_y) / res
        transform = Affine.translation(min_x, min_y) * Affine.scale(pw, ph)
        crs = CRS.from_epsg(int(crs_code.split(':')[1])) if crs_code.startswith('EPSG:') else CRS.from_string(crs_code)
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            tmp_path = tmp.name
        with rasterio.open(tmp_path, 'w', driver='GTiff', height=res, width=res, count=1, dtype=rasterio.float32, crs=crs, transform=transform, nodata=np.nan, compress='lzw', tiled=True) as dst:
            dst.write(Z_int.astype(rasterio.float32), 1)
        with open(tmp_path, 'rb') as f: data = f.read()
        os.unlink(tmp_path)
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def create_heatmap_geotiff(points_df, bounds, resolution=500, method='linear'):
    input_epsg = st.session_state.get("input_epsg", 32717)
    crs_code = f"EPSG:{input_epsg}"
    if points_df is not None and len(points_df) > 0:
        points_list = [[row['x'], row['y'], row['cota']] for _, row in points_df.iterrows()]
        return create_heatmap_geotiff_point_perfect(points_list=points_list, crs_code=crs_code, resolution=resolution, padding_percent=1.0, method=method)
    else:
        st.error("❌ No hay datos")
        return None
