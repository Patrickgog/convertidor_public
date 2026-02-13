from src.utils.helpers import points_equal

def parse_polygons_robust(df, epsilon=1e-6):
    """Parsea DataFrame de puntos en polígonos independientes de forma robusta"""
    points = []
    for idx, row in df.iterrows():
        try:
            x, y = float(row["x"]), float(row["y"])
            points.append((x, y))
        except Exception:
            continue
    
    if len(points) < 3:
        return []
    
    cleaned_points = [points[0]]
    for i in range(1, len(points)):
        if not points_equal(points[i], points[i-1], epsilon):
            cleaned_points.append(points[i])
    
    polygons = []
    i = 0
    while i < len(cleaned_points):
        polygon_start = cleaned_points[i]
        current_polygon = [polygon_start]
        j = i + 1
        polygon_closed = False
        while j < len(cleaned_points):
            current_point = cleaned_points[j]
            current_polygon.append(current_point)
            if points_equal(current_point, polygon_start, epsilon):
                polygon_closed = True
                if len(current_polygon) >= 4:
                    polygons.append(current_polygon)
                break
            j += 1
        if not polygon_closed and len(current_polygon) >= 3:
            current_polygon.append(polygon_start)
            polygons.append(current_polygon)
        i = j + 1 if polygon_closed else len(cleaned_points)
    return polygons

def parse_polygons_sequential(vertices, epsilon=0.01):
    def pts_eq(p1, p2, eps):
        return abs(p1[0]-p2[0]) < eps and abs(p1[1]-p2[1]) < eps
    
    polygons = []
    if not vertices: return polygons
    
    current_poly = [vertices[0]]
    for i in range(1, len(vertices)):
        current_poly.append(vertices[i])
        if pts_eq(vertices[i], current_poly[0], epsilon):
            if len(current_poly) >= 4:
                polygons.append(list(current_poly))
            if i + 1 < len(vertices):
                current_poly = [vertices[i+1]]
            else:
                current_poly = []
    if current_poly and len(current_poly) >= 3:
        if not pts_eq(current_poly[-1], current_poly[0], epsilon):
            current_poly.append(current_poly[0])
        polygons.append(current_poly)
    return polygons
