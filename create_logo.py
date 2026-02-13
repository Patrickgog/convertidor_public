"""
Script para generar el logo de la aplicación Conversor Universal Profesional
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_logo(output_path="assets/logo.png", size=400):
    """Crea el logo principal de la aplicación"""
    
    # Crear imagen con fondo blanco
    img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Colores
    primary_blue = (33, 150, 243, 255)      # #2196F3
    shadow_blue = (21, 101, 192, 255)        # #1565C0
    white = (255, 255, 255, 255)
    text_gray = (117, 117, 117, 255)         # #757575
    
    center_x = size // 2
    center_y = size // 2 - 30
    
    # Sombra (línea debajo)
    shadow_y = center_y + 130
    draw.rounded_rectangle(
        [center_x - 100, shadow_y, center_x + 100, shadow_y + 12],
        radius=6,
        fill=shadow_blue
    )
    
    # Círculo principal
    circle_radius = 90
    draw.ellipse(
        [center_x - circle_radius, center_y - circle_radius,
         center_x + circle_radius, center_y + circle_radius],
        fill=primary_blue
    )
    
    # Dibujar el icono de map-pin
    # Cuerpo del pin
    pin_points = [
        (center_x, center_y - 65),  # Punta superior
        (center_x - 40, center_y + 5),  # Base izquierda
        (center_x, center_y + 45),   # Punta inferior
        (center_x + 40, center_y + 5),   # Base derecha
    ]
    draw.polygon(pin_points, fill=white)
    
    # Círculo interno del pin
    inner_radius = 20
    draw.ellipse(
        [center_x - inner_radius, center_y - 25 - inner_radius,
         center_x + inner_radius, center_y - 25 + inner_radius],
        fill=primary_blue
    )
    
    # Punto central blanco
    dot_radius = 8
    draw.ellipse(
        [center_x - dot_radius, center_y - 25 - dot_radius,
         center_x + dot_radius, center_y - 25 + dot_radius],
        fill=white
    )
    
    # Intentar cargar fuentes
    try:
        font_title = ImageFont.truetype("arial.ttf", 32)
        font_subtitle = ImageFont.truetype("arial.ttf", 24)
    except:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
    
    # Texto del título
    title_text = "Conversor Universal"
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    title_width = bbox[2] - bbox[0]
    draw.text(
        (center_x - title_width // 2, size - 70),
        title_text,
        font=font_title,
        fill=primary_blue
    )
    
    # Texto subtítulo
    subtitle_text = "Profesional"
    bbox = draw.textbbox((0, 0), subtitle_text, font=font_subtitle)
    subtitle_width = bbox[2] - bbox[0]
    draw.text(
        (center_x - subtitle_width // 2, size - 38),
        subtitle_text,
        font=font_subtitle,
        fill=text_gray
    )
    
    # Guardar
    img.save(output_path, 'PNG')
    print(f"Logo guardado en: {output_path}")
    return img

def create_favicon(output_path="assets/favicon.png", size=64):
    """Crea el favicon de la aplicación"""
    
    # Crear imagen
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Colores
    primary_blue = (33, 150, 243, 255)      # #2196F3
    white = (255, 255, 255, 255)
    
    # Fondo cuadrado redondeado
    corner_radius = 12
    draw.rounded_rectangle(
        [0, 0, size, size],
        radius=corner_radius,
        fill=primary_blue
    )
    
    # Centro
    center_x = size // 2
    center_y = size // 2
    
    # Icono de map-pin simplificado
    pin_size = 20
    # Cuerpo del pin (triángulo)
    pin_points = [
        (center_x, center_y - pin_size),  # Arriba
        (center_x - pin_size//2, center_y + pin_size//3),  # Base izq
        (center_x, center_y + pin_size//1.5),  # Punta
        (center_x + pin_size//2, center_y + pin_size//3),  # Base der
    ]
    draw.polygon(pin_points, fill=white)
    
    # Círculo interno
    draw.ellipse(
        [center_x - 6, center_y - 10, center_x + 6, center_y + 2],
        fill=primary_blue
    )
    
    # Punto central
    draw.ellipse(
        [center_x - 3, center_y - 7, center_x + 3, center_y - 1],
        fill=white
    )
    
    # Guardar
    img.save(output_path, 'PNG')
    print(f"Favicon guardado en: {output_path}")
    return img

if __name__ == "__main__":
    # Asegurar que existe el directorio assets
    os.makedirs("assets", exist_ok=True)
    
    # Crear logo y favicon
    create_logo("assets/logo.png", size=400)
    create_favicon("assets/favicon.png", size=64)
    
    print("\nLogos creados exitosamente!")
    print("- assets/logo.png (400x400px) - Logo principal")
    print("- assets/favicon.png (64x64px) - Favicon")
    print("- assets/logo.svg - Version SVG del logo")