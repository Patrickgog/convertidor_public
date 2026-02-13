#!/usr/bin/env python3
"""
Ejemplo completo de generación de mapa de calor georeferenciado
Desarrollado por: Patricio Sarmiento Reinoso
Fecha: Septiembre 2025

Este script demuestra las mejores prácticas para generar mapas de calor
correctamente georeferenciados que se ubiquen correctamente en QGIS.
"""

import numpy as np
import pandas as pd
import tempfile
import os
from pathlib import Path

# Importaciones para geoprocesamiento
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS
from scipy.interpolate import griddata


def create_heatmap_geotiff_expert(points_list, bounds=None, resolution=500, method='cubic', crs_code='EPSG:32719'):
    """
    Función experta para crear mapas de calor georeferenciados correctamente.
    
    Esta función implementa las mejores prácticas de geoprocesamiento para generar
    un raster que se ubique correctamente en QGIS sin necesidad de georeferenciación manual.
    
    Args:
        points_list: Lista de puntos [[x1, y1, z1], [x2, y2, z2], ...]
        bounds: tuple (min_x, min_y, max_x, max_y) - opcional, se calcula automáticamente
        resolution: Resolución del raster (píxeles por lado)
        method: Método de interpolación ('linear', 'cubic', 'nearest')
        crs_code: Código CRS (ej. 'EPSG:32719' para UTM zona 19S)
    
    Returns:
        bytes: Contenido del archivo GeoTIFF correctamente georeferenciado
    """
    
    # === VALIDACIÓN DE ENTRADA ===
    if not points_list or len(points_list) < 3:
        raise ValueError("Se necesitan al menos 3 puntos para generar el mapa de calor")
    
    # Convertir a numpy arrays
    points_array = np.array(points_list)
    x_coords = points_array[:, 0]
    y_coords = points_array[:, 1]
    z_values = points_array[:, 2]
    
    # === PASO 1: CALCULAR BOUNDING BOX ===
    if bounds is None:
        min_x, max_x = x_coords.min(), x_coords.max()
        min_y, max_y = y_coords.min(), y_coords.max()
        
        # Agregar margen del 10%
        x_range = max_x - min_x
        y_range = max_y - min_y
        margin_x = x_range * 0.1
        margin_y = y_range * 0.1
        
        bounds = (min_x - margin_x, min_y - margin_y, max_x + margin_x, max_y + margin_y)
    
    min_x, min_y, max_x, max_y = bounds
    
    # === PASO 2: CREAR GRID REGULAR ===
    # Asegurar resolución mínima
    actual_resolution = max(resolution, 100)
    
    # Crear arrays de coordenadas para el grid
    x_grid = np.linspace(min_x, max_x, actual_resolution)
    y_grid = np.linspace(min_y, max_y, actual_resolution)
    
    # Crear meshgrid con orientación correcta
    # Usar indexing='xy' para evitar inversión horizontal
    X_grid, Y_grid = np.meshgrid(x_grid, y_grid, indexing='xy')
    
    # === PASO 3: INTERPOLACIÓN ===
    # Preparar puntos de entrada para interpolación
    points = np.column_stack((x_coords, y_coords))
    
    # Interpolar valores Z en el grid
    Z_interpolated = griddata(
        points, 
        z_values, 
        (X_grid, Y_grid), 
        method=method, 
        fill_value=np.nan
    )
    
    # === PASO 4: CALCULAR TRANSFORMACIÓN AFÍN ===
    # Calcular tamaño de píxel en unidades del CRS
    pixel_width = (max_x - min_x) / actual_resolution
    pixel_height = (max_y - min_y) / actual_resolution
    
    # Crear transformación afín correcta
    # Para indexing='xy', la transformación debe ser:
    # Píxel (0,0) -> coordenada (min_x, max_y) [esquina superior izquierda]
    # Píxel (width, height) -> coordenada (max_x, min_y) [esquina inferior derecha]
    
    transform = Affine.translation(min_x, max_y) * Affine.scale(pixel_width, -pixel_height)
    
    # === PASO 5: CONFIGURAR CRS ===
    # Crear objeto CRS
    if crs_code.startswith('EPSG:'):
        epsg_code = int(crs_code.split(':')[1])
        crs = CRS.from_epsg(epsg_code)
    else:
        # Fallback para otros códigos CRS
        crs = CRS.from_string(crs_code)
    
    # === PASO 6: ESCRIBIR GEOTIFF ===
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Escribir GeoTIFF con configuración completa
        with rasterio.open(
            temp_path,
            'w',
            driver='GTiff',
            height=actual_resolution,
            width=actual_resolution,
            count=1,
            dtype=rasterio.float32,
            crs=crs,  # CRS específico para georeferenciación correcta
            transform=transform,  # Transformación afín correcta
            nodata=np.nan,  # Valor NoData
            compress='lzw',  # Compresión para reducir tamaño
            tiled=True,  # Tiled para mejor rendimiento
            blockxsize=256,
            blockysize=256,
            interleave='band',
            photometric='minisblack'  # Para datos de elevación/intensidad
        ) as dst:
            # Escribir datos interpolados
            dst.write(Z_interpolated.astype(rasterio.float32), 1)
            
            # Agregar metadatos descriptivos
            dst.update_tags(
                SOFTWARE="Heatmap Expert v1.0",
                DESCRIPTION=f"Mapa de calor - Método: {method}, Resolución: {actual_resolution}x{actual_resolution}",
                CRS=crs_code,
                INTERPOLATION_METHOD=method,
                POINTS_COUNT=len(points_list),
                BOUNDS=f"{min_x:.6f},{min_y:.6f},{max_x:.6f},{max_y:.6f}"
            )
        
        # Leer el archivo generado
        with open(temp_path, 'rb') as f:
            geotiff_bytes = f.read()
        
        return geotiff_bytes
        
    finally:
        # Limpiar archivo temporal
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def create_sample_data():
    """
    Crea datos de ejemplo para probar el mapa de calor.
    
    Returns:
        list: Lista de puntos de ejemplo en UTM zona 19S
    """
    # Datos de ejemplo: puntos en UTM zona 17S (Ecuador) - EPSG:32717
    sample_points = [
        [200000, 9800000, 2450],  # Punto 1
        [200100, 9800000, 2445],  # Punto 2
        [200200, 9800000, 2440],  # Punto 3
        [200000, 9800100, 2455],  # Punto 4
        [200100, 9800100, 2450],  # Punto 5
        [200200, 9800100, 2445],  # Punto 6
        [200050, 9800050, 2448],  # Punto 7
        [200150, 9800050, 2443],  # Punto 8
        [200250, 9800050, 2438],  # Punto 9
        [200075, 9800075, 2446],  # Punto 10
        [200125, 9800025, 2441],  # Punto 11
        [200175, 9800075, 2444],  # Punto 12
    ]
    
    return sample_points


def main():
    """
    Función principal que demuestra el uso del generador de mapas de calor.
    """
    print("🗺️ Generador de Mapas de Calor Georeferenciados")
    print("=" * 50)
    
    # Crear datos de ejemplo
    points = create_sample_data()
    print(f"📊 Puntos de ejemplo: {len(points)} puntos")
    
    # Mostrar información de los puntos
    print("\n📍 Coordenadas de los puntos:")
    for i, (x, y, z) in enumerate(points, 1):
        print(f"  P{i:2d}: X={x:8.0f}, Y={y:8.0f}, Z={z:6.1f}")
    
    # Calcular bounds
    points_array = np.array(points)
    min_x, max_x = points_array[:, 0].min(), points_array[:, 0].max()
    min_y, max_y = points_array[:, 1].min(), points_array[:, 1].max()
    
    print(f"\n📐 Bounds del área:")
    print(f"  X: {min_x:.0f} - {max_x:.0f} (rango: {max_x-min_x:.0f})")
    print(f"  Y: {min_y:.0f} - {max_y:.0f} (rango: {max_y-min_y:.0f})")
    
    # Generar mapa de calor
    print(f"\n🔄 Generando mapa de calor...")
    
    try:
        # Generar GeoTIFF
        geotiff_bytes = create_heatmap_geotiff_expert(
            points_list=points,
            resolution=500,
            method='cubic',
            crs_code='EPSG:32717'
        )
        
        # Guardar archivo
        output_path = Path("heatmap_example.tif")
        with open(output_path, 'wb') as f:
            f.write(geotiff_bytes)
        
        print(f"✅ Mapa de calor generado exitosamente: {output_path}")
        print(f"📁 Tamaño del archivo: {len(geotiff_bytes) / 1024:.1f} KB")
        
        # Información adicional
        print(f"\n🌍 CRS: EPSG:32717 (UTM Zona 17S - Ecuador)")
        print(f"📊 Resolución: 500x500 píxeles")
        print(f"🔬 Método de interpolación: Cúbica")
        
        print(f"\n💡 Instrucciones para QGIS:")
        print(f"  1. Abre QGIS")
        print(f"  2. Carga el archivo: {output_path}")
        print(f"  3. El raster debería aparecer correctamente ubicado")
        print(f"  4. Aplica un estilo de mapa de calor")
        print(f"  5. Los puntos originales deberían coincidir con el raster")
        
    except Exception as e:
        print(f"❌ Error al generar mapa de calor: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🎉 ¡Ejemplo completado exitosamente!")
    else:
        print(f"\n💥 El ejemplo falló. Revisa los errores arriba.")
