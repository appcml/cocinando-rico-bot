#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍳 Bot de Recetas "Cocinando Rico" para Facebook - V1.1 (CORREGIDO)
"""

import requests
import json
import os
import re
import hashlib
import sys
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from PIL import Image, ImageDraw, ImageFont
import textwrap

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN - Cargar desde .env si existe
# ═══════════════════════════════════════════════════════════════

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️ python-dotenv no instalado, usando variables de entorno del sistema")

# APIs
THEMEALDB_API = "https://www.themealdb.com/api/json/v1/1"

# Facebook (REQUERIDO)
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

# Edamam (OPCIONAL)
EDAMAM_APP_ID = os.getenv('EDAMAM_APP_ID')
EDAMAM_API_KEY = os.getenv('EDAMAM_API_KEY')

# Rutas - CORREGIDO: Crear directorios automáticamente
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', os.path.join(DATA_DIR, 'historial_recetas.json'))
ESTADO_PATH = os.getenv('ESTADO_PATH', os.path.join(DATA_DIR, 'estado_bot.json'))

# Tiempos
TIEMPO_ENTRE_PUBLICACIONES = int(os.getenv('TIEMPO_ENTRE_PUBLICACIONES', '1'))  # 1 min para pruebas, cambiar a 360 para producción
UMBRAL_SIMILITUD = 0.75
MAX_HISTORIAL = 100

# ═══════════════════════════════════════════════════════════════
# SISTEMA DE LOGGING MEJORADO
# ═══════════════════════════════════════════════════════════════

def log(mensaje, tipo='info'):
    iconos = {
        'info': 'ℹ️', 
        'exito': '✅', 
        'error': '❌', 
        'advertencia': '⚠️', 
        'cocina': '👨‍🍳',
        'debug': '🔍',
        'facebook': '📘',
        'api': '🌐'
    }
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {iconos.get(tipo, 'ℹ️')} {mensaje}", flush=True)

# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ═══════════════════════════════════════════════════════════════

def cargar_json(ruta, default=None):
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return default.copy()
                return json.loads(content)
        except json.JSONDecodeError as e:
            log(f"JSON corrupto en {ruta}: {e}", 'error')
            # Backup del archivo corrupto
            backup = f"{ruta}.corrupto.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                os.rename(ruta, backup)
                log(f"Backup creado: {backup}", 'advertencia')
            except:
                pass
            return default.copy()
        except Exception as e:
            log(f"Error cargando {ruta}: {e}", 'error')
            return default.copy()
    return default.copy()

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        temp_path = f"{ruta}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, ruta)
        return True
    except Exception as e:
        log(f"Error guardando JSON: {e}", 'error')
        return False

def generar_hash(texto):
    if not texto:
        return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def calcular_similitud(s1, s2):
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

# ═══════════════════════════════════════════════════════════════
# GESTIÓN DE RECETAS
# ═══════════════════════════════════════════════════════════════

class GestorRecetas:
    def __init__(self):
        self.historial = self.cargar_historial()
        
    def cargar_historial(self):
        default = {
            'ids_recetas': [],
            'hashes': [],
            'timestamps': [],
            'nombres': [],
            'categorias': [],
            'estadisticas': {'total_publicadas': 0}
        }
        h = cargar_json(HISTORIAL_PATH, default)
        # Asegurar que todas las claves existan
        for k in default:
            if k not in h:
                h[k] = default[k]
        self.limpiar_historial_antiguo(h)
        return h
    
    def limpiar_historial_antiguo(self, h):
        try:
            ahora = datetime.now()
            indices_mantener = []
            for i, ts in enumerate(h.get('timestamps', [])):
                try:
                    fecha = datetime.fromisoformat(ts)
                    if (ahora - fecha).days < 30:
                        indices_mantener.append(i)
                except:
                    continue
            
            for key in ['ids_recetas', 'hashes', 'timestamps', 'nombres', 'categorias']:
                if key in h and isinstance(h[key], list):
                    h[key] = [h[key][i] for i in indices_mantener if i < len(h[key])]
        except Exception as e:
            log(f"Error limpiando historial: {e}", 'error')
    
    def receta_ya_publicada(self, id_receta, nombre):
        hash_nombre = generar_hash(nombre)
        
        # Verificar por ID
        if id_receta in self.historial.get('ids_recetas', []):
            return True, "id_duplicado"
        
        # Verificar por hash exacto
        if hash_nombre in self.historial.get('hashes', []):
            return True, "hash_duplicado"
        
        # Verificar similitud de nombre
        for nombre_hist in self.historial.get('nombres', []):
            sim = calcular_similitud(nombre, nombre_hist)
            if sim >= UMBRAL_SIMILITUD:
                return True, f"similitud_{sim:.2f}"
        
        return False, "nueva"
    
    def guardar_receta(self, id_receta, nombre, categoria):
        hash_nombre = generar_hash(nombre)
        
        self.historial['ids_recetas'].append(id_receta)
        self.historial['hashes'].append(hash_nombre)
        self.historial['timestamps'].append(datetime.now().isoformat())
        self.historial['nombres'].append(nombre)
        self.historial['categorias'].append(categoria)
        self.historial['estadisticas']['total_publicadas'] = \
            self.historial['estadisticas'].get('total_publicadas', 0) + 1
        
        # Limitar tamaño
        for key in ['ids_recetas', 'hashes', 'timestamps', 'nombres', 'categorias']:
            if len(self.historial[key]) > MAX_HISTORIAL:
                self.historial[key] = self.historial[key][-MAX_HISTORIAL:]
        
        if guardar_json(HISTORIAL_PATH, self.historial):
            log(f"💾 Receta guardada. Total histórico: {self.historial['estadisticas']['total_publicadas']}", 'exito')
        else:
            log("❌ Error guardando historial", 'error')

# ═══════════════════════════════════════════════════════════════
# OBTENCIÓN DE RECETAS - CON MÁS DEBUGGING
# ═══════════════════════════════════════════════════════════════

def obtener_receta_aleatoria():
    """Obtiene una receta aleatoria de TheMealDB"""
    try:
        log("🌐 Solicitando receta aleatoria a TheMealDB...", 'api')
        url = f"{THEMEALDB_API}/random.php"
        response = requests.get(url, timeout=15)
        
        log(f"   ↳ Status: {response.status_code}", 'debug')
        
        if response.status_code != 200:
            log(f"   ❌ Error HTTP {response.status_code}", 'error')
            return None
        
        data = response.json()
        
        if not data:
            log("   ❌ Respuesta vacía", 'error')
            return None
            
        if not data.get('meals'):
            log("   ❌ No hay recetas en la respuesta", 'error')
            return None
            
        receta = procesar_receta_themealdb(data['meals'][0])
        log(f"   ✅ Receta obtenida: {receta['nombre'][:50]}", 'exito')
        return receta
        
    except requests.exceptions.Timeout:
        log("   ❌ Timeout al conectar con TheMealDB", 'error')
        return None
    except requests.exceptions.ConnectionError:
        log("   ❌ Error de conexión con TheMealDB", 'error')
        return None
    except Exception as e:
        log(f"   ❌ Error inesperado: {e}", 'error')
        return None

def obtener_receta_por_categoria(categoria):
    """Obtiene recetas por categoría"""
    try:
        log(f"🌐 Buscando en categoría: {categoria}", 'api')
        url = f"{THEMEALDB_API}/filter.php?c={categoria}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if not data or not data.get('meals'):
            log(f"   ⚠️ Sin resultados para categoría {categoria}", 'advertencia')
            return None
        
        import random
        receta_basica = random.choice(data['meals'])
        return obtener_detalles_receta(receta_basica['idMeal'])
        
    except Exception as e:
        log(f"Error en categoría {categoria}: {e}", 'error')
        return None

def obtener_detalles_receta(id_receta):
    """Obtiene detalles completos de una receta por ID"""
    try:
        url = f"{THEMEALDB_API}/lookup.php?i={id_receta}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if data and data.get('meals'):
            return procesar_receta_themealdb(data['meals'][0])
        return None
    except Exception as e:
        log(f"Error obteniendo detalles: {e}", 'error')
        return None

def procesar_receta_themealdb(datos):
    """Procesa los datos crudos de TheMealDB"""
    receta = {
        'id': datos.get('idMeal'),
        'nombre': datos.get('strMeal', 'Sin nombre'),
        'categoria': datos.get('strCategory', 'Plato'),
        'area': datos.get('strArea', 'Internacional'),
        'instrucciones': datos.get('strInstructions', ''),
        'imagen': datos.get('strMealThumb'),
        'video': datos.get('strYoutube', ''),
        'fuente': datos.get('strSource') or 'TheMealDB',
        'ingredientes': []
    }
    
    # Extraer ingredientes y medidas (hasta 20)
    for i in range(1, 21):
        ingrediente = datos.get(f'strIngredient{i}')
        medida = datos.get(f'strMeasure{i}')
        
        if ingrediente and str(ingrediente).strip():
            receta['ingredientes'].append({
                'nombre': str(ingrediente).strip(),
                'cantidad': str(medida).strip() if medida else 'al gusto'
            })
    
    return receta

# ═══════════════════════════════════════════════════════════════
# GENERACIÓN DE CONTENIDO
# ═══════════════════════════════════════════════════════════════

def formatear_ingredientes(ingredientes):
    if not ingredientes:
        return "• Ingredientes no disponibles"
    
    lineas = []
    for ing in ingredientes[:10]:  # Máximo 10 ingredientes para Facebook
        cantidad = ing.get('cantidad', '')
        nombre = ing.get('nombre', '')
        emoji = obtener_emoji_ingrediente(nombre)
        
        if cantidad and cantidad.lower() != 'al gusto':
            lineas.append(f"{emoji} {cantidad} {nombre}")
        else:
            lineas.append(f"{emoji} {nombre}")
    
    return '\n'.join(lineas)

def obtener_emoji_ingrediente(ingrediente):
    """Devuelve emoji según el ingrediente"""
    ingrediente_lower = ingrediente.lower()
    emojis = {
        'chicken': '🍗', 'pollo': '🍗',
        'beef': '🥩', 'carne': '🥩', 'meat': '🥩',
        'fish': '🐟', 'pescado': '🐟', 'salmon': '🐟',
        'pasta': '🍝', 'spaghetti': '🍝',
        'rice': '🍚', 'arroz': '🍚',
        'tomato': '🍅', 'tomate': '🍅',
        'onion': '🧅', 'cebolla': '🧅',
        'garlic': '🧄', 'ajo': '🧄',
        'potato': '🥔', 'papa': '🥔', 'patata': '🥔',
        'cheese': '🧀', 'queso': '🧀',
        'milk': '🥛', 'leche': '🥛',
        'egg': '🥚', 'huevo': '🥚',
        'butter': '🧈', 'mantequilla': '🧈',
        'oil': '🛢️', 'aceite': '🛢️',
        'salt': '🧂', 'sal': '🧂',
        'pepper': '🌶️', 'pimienta': '🌶️',
        'sugar': '🍬', 'azucar': '🍬',
        'flour': '🌾', 'harina': '🌾',
        'water': '💧', 'agua': '💧',
        'wine': '🍷', 'vino': '🍷',
        'lemon': '🍋', 'limon': '🍋',
        'default': '•'
    }
    
    for key, emoji in emojis.items():
        if key in ingrediente_lower:
            return emoji
    return emojis['default']

def formatear_instrucciones(instrucciones):
    if not instrucciones:
        return "Instrucciones no disponibles. Visita el enlace de la fuente."
    
    # Limpiar texto
    texto = instrucciones.replace('\r', '\n').strip()
    
    # Dividir en pasos (por números o saltos de línea)
    pasos = []
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    for linea in lineas:
        # Si la línea empieza con número, limpiarlo
        linea_limpia = re.sub(r'^\d+[\.\)]\s*', '', linea)
        if len(linea_limpia) > 20:
            pasos.append(linea_limpia)
    
    # Si no se detectaron pasos, dividir por oraciones
    if len(pasos) < 2:
        oraciones = [o.strip() for o in texto.split('.') if len(o.strip()) > 30]
        pasos = oraciones
    
    # Formatear máximo 4 pasos para Facebook
    pasos_formateados = []
    for i, paso in enumerate(pasos[:4], 1):
        if len(paso) > 180:
            paso = paso[:177] + "..."
        pasos_formateados.append(f"{i}. {paso}")
    
    return '\n\n'.join(pasos_formateados)

def construir_publicacion(receta):
    """Construye el texto de la publicación para Facebook"""
    nombre = receta['nombre']
    categoria = receta.get('categoria', 'Plato')
    area = receta.get('area', 'Internacional')
    
    lineas = [
        f"🍳 {nombre}",
        "",
        f"📍 {area} • {categoria}",
        "",
        "📝 INGREDIENTES:",
        formatear_ingredientes(receta.get('ingredientes', [])),
        "",
        "👨‍🍳 PREPARACIÓN:",
        formatear_instrucciones(receta.get('instrucciones', '')),
        "",
        "─────────────────",
        "💡 ¿La preparaste? Cuéntanos cómo te quedó en los comentarios 👇",
    ]
    
    # Añadir fuente si existe
    if receta.get('fuente') and receta['fuente'] != 'TheMealDB':
        lineas.append(f"")
        lineas.append(f"🔗 Receta completa: {receta['fuente']}")
    
    return '\n'.join(lineas)

def generar_hashtags(receta):
    nombre = receta.get('nombre', '').lower()
    categoria = receta.get('categoria', '').lower()
    area = receta.get('area', '').lower()
    
    hashtags = ['#CocinandoRico', '#Recetas', '#CocinaCasera']
    
    # Hashtags por categoría
    if any(p in categoria for p in ['dessert', 'postre']):
        hashtags.extend(['#Postres', '#Reposteria', '#Dulces'])
    elif any(p in categoria for p in ['chicken', 'pollo']):
        hashtags.extend(['#Pollo', '#RecetasConPollo'])
    elif any(p in categoria for p in ['beef', 'carne', 'res']):
        hashtags.extend(['#Carne', '#Res', '#Parrilla'])
    elif any(p in categoria for p in ['pasta']):
        hashtags.extend(['#Pasta', '#ComidaItaliana'])
    elif any(p in categoria for p in ['seafood', 'marisco']):
        hashtags.extend(['#Mariscos', '#Pescado'])
    elif any(p in categoria for p in ['vegetarian', 'vegan']):
        hashtags.extend(['#Vegetariano', '#Vegano', '#Saludable'])
    else:
        hashtags.extend(['#RecetaDelDia', '#ComidaDeliciosa'])
    
    # Hashtags por área
    areas = {
        'italian': '#CocinaItaliana',
        'mexican': '#CocinaMexicana',
        'spanish': '#CocinaEspañola',
        'chinese': '#CocinaChina',
        'french': '#CocinaFrancesa',
        'indian': '#CocinaHindu',
        'american': '#CocinaAmericana',
        'thai': '#CocinaThai'
    }
    
    for key, tag in areas.items():
        if key in area:
            hashtags.append(tag)
            break
    
    return ' '.join(hashtags)

# ═══════════════════════════════════════════════════════════════
# IMÁGENES - CORREGIDO PARA FACEBOOK 2024
# ═══════════════════════════════════════════════════════════════

def descargar_imagen_receta(url_imagen):
    """Descarga imagen con validaciones estrictas para Facebook"""
    if not url_imagen:
        log("   ⚠️ URL de imagen vacía", 'advertencia')
        return None
    
    # Validar URL
    if not url_imagen.startswith(('http://', 'https://')):
        log(f"   ⚠️ URL inválida: {url_imagen[:50]}", 'advertencia')
        return None
    
    try:
        from io import BytesIO
        
        log(f"   🌐 Descargando imagen...", 'debug')
        
        # Headers necesarios para Facebook
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url_imagen, headers=headers, timeout=20, stream=True)
        
        if response.status_code != 200:
            log(f"   ❌ HTTP {response.status_code} al descargar imagen", 'error')
            return None
        
        # Verificar Content-Type
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            log(f"   ⚠️ Content-Type no es imagen: {content_type}", 'advertencia')
            # Intentar igual si el contenido parece válido
        
        # Verificar tamaño
        content_length = response.headers.get('content-length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > 8:  # Facebook límite ~8MB
                log(f"   ⚠️ Imagen muy grande: {size_mb:.1f}MB", 'advertencia')
                return None
        
        img = Image.open(BytesIO(response.content))
        
        # Validar formato
        if img.format not in ['JPEG', 'JPG', 'PNG', 'GIF', 'WEBP']:
            log(f"   ⚠️ Formato no soportado: {img.format}", 'advertencia')
            return None
        
        w, h = img.size
        log(f"   📐 Imagen original: {w}x{h} ({img.format})", 'debug')
        
        # Validaciones de tamaño Facebook
        if w < 200 or h < 200:
            log(f"   ❌ Imagen muy pequeña (min 200x200)", 'error')
            return None
        
        # Convertir a RGB si es necesario
        if img.mode in ('RGBA', 'P', 'LA', 'L'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            else:
                img = img.convert('RGB')
        
        # Redimensionar manteniendo proporción (Facebook recomienda 1200x630)
        max_size = (1200, 1200)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Si es muy horizontal o vertical, ajustar
        w, h = img.size
        ratio = w / h
        
        if ratio > 3 or ratio < 0.3:
            log(f"   ⚠️ Proporción extrema {ratio:.2f}, ajustando...", 'advertencia')
            # Añadir padding para hacerla más cuadrada
            new_size = max(w, h)
            new_img = Image.new('RGB', (new_size, new_size), (255, 255, 255))
            x = (new_size - w) // 2
            y = (new_size - h) // 2
            new_img.paste(img, (x, y))
            img = new_img
        
        # Guardar con calidad óptima para Facebook
        hash_img = generar_hash(url_imagen)[:10]
        path = os.path.join('/tmp', f'receta_{hash_img}.jpg')
        
        # Guardar con calidad 85% (balance tamaño/calidad)
        img.save(path, 'JPEG', quality=85, optimize=True)
        
        # Verificar tamaño final
        final_size = os.path.getsize(path) / (1024 * 1024)
        log(f"   💾 Imagen guardada: {path} ({final_size:.2f}MB)", 'exito')
        
        if final_size > 8:
            log(f"   ⚠️ Comprimiendo más...", 'advertencia')
            img.save(path, 'JPEG', quality=70, optimize=True)
        
        return path
        
    except Exception as e:
        log(f"   ❌ Error procesando imagen: {e}", 'error')
        return None

def crear_imagen_receta(nombre_receta, categoria, area):
    """Crea imagen personalizada si falla la descarga"""
    try:
        log("   🎨 Creando imagen personalizada...", 'cocina')
        
        # Colores según categoría
        paletas = {
            'Dessert': ('#8B4513', '#FFD700', '#FFF8DC'),      # Marrón/Dorado/Crema
            'Seafood': ('#1E3A5F', '#87CEEB', '#E0F6FF'),      # Azul marino
            'Vegetarian': ('#228B22', '#90EE90', '#F0FFF0'),   # Verde
            'Vegan': ('#2E8B57', '#98FB98', '#F5FFFA'),
            'Chicken': ('#DAA520', '#FFE4B5', '#FFFAF0'),      # Dorado
            'Beef': ('#8B0000', '#FFA07A', '#FFE4E1'),        # Rojo
            'Pasta': ('#FF6347', '#FFD700', '#FFFACD'),        # Tomate/Dorado
            'Lamb': ('#800080', '#DDA0DD', '#FFF0FF'),        # Púrpura
            'Pork': ('#FF69B4', '#FFB6C1', '#FFF0F5'),        # Rosa
            'Breakfast': ('#FFA500', '#FFDEAD', '#FFFAF0'),    # Naranja
        }
        
        bg_color, accent_color, text_bg = paletas.get(categoria, ('#FF6B35', '#FFE66D', '#FFF5EE'))
        
        # Crear imagen 1200x630 (óptimo para Facebook)
        img = Image.new('RGB', (1200, 630), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Intentar cargar fuentes del sistema
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # Mac
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows
        ]
        
        try:
            # Intentar cargar fuentes, si no existe usar default
            font_title = ImageFont.truetype(font_paths[0], 52)
            font_sub = ImageFont.truetype(font_paths[1], 32)
            font_small = ImageFont.truetype(font_paths[1], 24)
        except:
            font_title = font_sub = font_small = ImageFont.load_default()
        
        # Barra decorativa superior
        draw.rectangle([(0, 0), (1200, 15)], fill=accent_color)
        
        # Área de texto con fondo semi-transparente (simulado con rectángulo)
        draw.rectangle([(50, 150), (1150, 480)], fill=text_bg)
        
        # Título centrado y envuelto
        titulo = textwrap.fill(nombre_receta[:80], width=28)
        y_pos = 200
        
        # Dibujar título (simulando centrado manual)
        draw.text((100, y_pos), titulo, font=font_title, fill='#333333')
        
        # Categoría y área
        info = f"🍳 {area} • {categoria}"
        draw.text((100, 400), info, font=font_sub, fill=bg_color)
        
        # Footer con branding
        draw.rectangle([(0, 580), (1200, 630)], fill='#2C3E50')
        draw.text((600, 605), "Cocinando Rico 🥘 Recetas deliciosas para cada día", 
                 font=font_small, fill='white', anchor="mm")
        
        # Guardar
        hash_nombre = generar_hash(nombre_receta)[:10]
        path = os.path.join('/tmp', f'receta_gen_{hash_nombre}.jpg')
        img.save(path, 'JPEG', quality=90, optimize=True)
        
        log(f"   ✅ Imagen generada: {path}", 'exito')
        return path
        
    except Exception as e:
        log(f"   ❌ Error creando imagen: {e}", 'error')
        return None

# ═══════════════════════════════════════════════════════════════
# FACEBOOK - CORREGIDO PARA API v18 (2024)
# ═══════════════════════════════════════════════════════════════

def publicar_facebook(texto, imagen_path, hashtags):
    """Publica en Facebook con manejo de errores detallado"""
    if not FB_PAGE_ID:
        log("❌ ERROR: FB_PAGE_ID no configurado", 'error')
        return False
    
    if not FB_ACCESS_TOKEN:
        log("❌ ERROR: FB_ACCESS_TOKEN no configurado", 'error')
        return False
    
    # Verificar que el token no sea el ejemplo
    if FB_ACCESS_TOKEN == 'tu_token_de_acceso_aqui':
        log("❌ ERROR: Token de Facebook es el valor de ejemplo", 'error')
        return False
    
    log(f"📘 Publicando en Facebook...", 'facebook')
    log(f"   ↳ Page ID: {FB_PAGE_ID[:10]}...", 'debug')
    log(f"   ↳ Token: {FB_ACCESS_TOKEN[:20]}...", 'debug')
    
    # Preparar mensaje
    mensaje = f"{texto}\n\n{hashtags}\n\n— 🍳 Cocinando Rico | Recetas deliciosas para cada día"
    
    # Truncar si es muy largo (límite Facebook ~2200 chars)
    if len(mensaje) > 2200:
        log(f"   ✂️ Mensaje truncado (era {len(mensaje)} chars)", 'advertencia')
        lineas = texto.split('\n')
        texto_cortado = ""
        for linea in lineas:
            if len(texto_cortado + linea + "\n") < 1800:
                texto_cortado += linea + "\n"
            else:
                break
        mensaje = f"{texto_cortado.rstrip()}\n\n[Receta completa en comentarios]\n\n{hashtags}\n\n— 🍳 Cocinando Rico"
    
    # Verificar imagen
    if not os.path.exists(imagen_path):
        log(f"   ❌ Archivo de imagen no existe: {imagen_path}", 'error')
        return False
    
    file_size = os.path.getsize(imagen_path)
    log(f"   📎 Archivo: {imagen_path} ({file_size/1024:.1f}KB)", 'debug')
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            files = {
                'file': ('receta.jpg', f, 'image/jpeg')
            }
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN,
                'published': 'true'
            }
            
            log("   🌐 Enviando a Facebook Graph API...", 'facebook')
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            log(f"   ↳ Status HTTP: {response.status_code}", 'debug')
            
            if 'id' in result:
                log(f"   ✅ PUBLICADO EXITOSAMENTE", 'exito')
                log(f"   📋 Post ID: {result['id']}", 'exito')
                if 'post_id' in result:
                    log(f"   🔗 https://facebook.com/{result['post_id']}", 'exito')
                return True
            else:
                error = result.get('error', {})
                error_code = error.get('code', 'unknown')
                error_msg = error.get('message', 'Error desconocido')
                error_type = error.get('type', 'unknown')
                
                log(f"   ❌ ERROR FACEBOOK ({error_code}): {error_msg}", 'error')
                log(f"   📋 Tipo: {error_type}", 'error')
                
                # Mensajes de ayuda según el error
                if error_code == 190:
                    log("   💡 El token de acceso ha expirado o es inválido. Genera uno nuevo.", 'advertencia')
                elif error_code == 200:
                    log("   💡 Permisos insuficientes. Verifica que el token tenga 'pages_manage_posts'.", 'advertencia')
                elif error_code == 100:
                    log("   💡 Error de parámetros. Verifica el ID de la página.", 'advertencia')
                elif error_code == 1:
                    log("   💡 Error genérico de API. Intenta nuevamente.", 'advertencia')
                elif 'image' in error_msg.lower() or 'photo' in error_msg.lower():
                    log("   💡 Problema con la imagen. Intenta usar otra URL o generar imagen local.", 'advertencia')
                
                return False
                
    except requests.exceptions.Timeout:
        log("   ❌ Timeout al conectar con Facebook", 'error')
        return False
    except requests.exceptions.ConnectionError:
        log("   ❌ Error de conexión con Facebook", 'error')
        return False
    except Exception as e:
        log(f"   ❌ Excepción inesperada: {e}", 'error')
        import traceback
        traceback.print_exc()
        return False

# ═══════════════════════════════════════════════════════════════
# FLUJO PRINCIPAL - CON VALIDACIONES
# ═══════════════════════════════════════════════════════════════

def verificar_tiempo():
    """Verifica tiempo entre publicaciones"""
    estado = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    ultima = estado.get('ultima_publicacion')
    
    if not ultima:
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        minutos = (datetime.now() - ultima_dt).total_seconds() / 60
        
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última publicación hace {minutos:.0f} min (mín: {TIEMPO_ENTRE_PUBLICACIONES})", 'info')
            return False
        else:
            log(f"⏱️ Tiempo transcurrido: {minutos:.0f} min - OK", 'info')
    except Exception as e:
        log(f"⚠️ Error parseando fecha: {e}", 'advertencia')
    
    return True

def seleccionar_receta(gestor):
    """Selecciona receta con múltiples intentos"""
    categorias_intentar = ['Dessert', 'Chicken', 'Pasta', 'Seafood', 'Vegetarian', 'Beef']
    max_intentos = 20
    
    log(f"🔍 Buscando receta (máx {max_intentos} intentos)...", 'cocina')
    
    for intento in range(max_intentos):
        log(f"   Intento {intento + 1}/{max_intentos}...", 'debug')
        
        # Estrategia 1: Aleatoria (más probable)
        receta = obtener_receta_aleatoria()
        
        # Estrategia 2: Por categoría si la aleatoria falla
        if not receta and intento > 5:
            cat = categorias_intentar[intento % len(categorias_intentar)]
            receta = obtener_receta_por_categoria(cat)
        
        if not receta:
            continue
        
        id_receta = receta.get('id')
        nombre = receta.get('nombre')
        
        if not id_receta or not nombre:
            log(f"   ⚠️ Receta sin ID o nombre", 'advertencia')
            continue
        
        # Verificar duplicados
        es_dup, razon = gestor.receta_ya_publicada(id_receta, nombre)
        if es_dup:
            log(f"   ↳ Duplicado ({razon}): {nombre[:40]}...", 'debug')
            continue
        
        # Validar contenido mínimo
        if len(receta.get('ingredientes', [])) < 2:
            log(f"   ⚠️ Pocos ingredientes ({len(receta.get('ingredientes', []))})", 'advertencia')
            continue
        
        if len(receta.get('instrucciones', '')) < 50:
            log(f"   ⚠️ Instrucciones muy cortas", 'advertencia')
            continue
        
        log(f"   ✅ SELECCIONADA: {nombre}", 'exito')
        return receta
    
    log("❌ No se encontró receta válida tras todos los intentos", 'error')
    return None

def main():
    """Función principal con manejo de errores completo"""
    print("\n" + "="*70)
    print("🍳 COCINANDO RICO BOT - V1.1 (CORREGIDO)")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # ═══════════════════════════════════════════════════════════════
    # VALIDACIONES INICIALES
    # ═══════════════════════════════════════════════════════════════
    
    errores = []
    
    # 1. Verificar Python version
    if sys.version_info < (3, 7):
        errores.append("Python 3.7+ requerido")
    
    # 2. Verificar credenciales Facebook
    if not FB_PAGE_ID:
        errores.append("FB_PAGE_ID no configurado")
    elif FB_PAGE_ID == 'tu_page_id_aqui':
        errores.append("FB_PAGE_ID es el valor de ejemplo")
    
    if not FB_ACCESS_TOKEN:
        errores.append("FB_ACCESS_TOKEN no configurado")
    elif FB_ACCESS_TOKEN == 'tu_token_de_acceso_aqui':
        errores.append("FB_ACCESS_TOKEN es el valor de ejemplo")
    
    # 3. Verificar directorios
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            log(f"📁 Directorio creado: {DATA_DIR}", 'exito')
        except Exception as e:
            errores.append(f"No se puede crear directorio data: {e}")
    
    # 4. Verificar dependencias
    try:
        from PIL import Image
    except ImportError:
        errores.append("Pillow no instalado (pip install Pillow)")
    
    try:
        import requests
    except ImportError:
        errores.append("requests no instalado (pip install requests)")
    
    if errores:
        log("❌ ERRORES CRÍTICOS DETECTADOS:", 'error')
        for i, error in enumerate(errores, 1):
            log(f"   {i}. {error}", 'error')
        log("\n💡 Solución: Configura el archivo .env con valores reales", 'advertencia')
        return False
    
    log("✅ Configuración válida", 'exito')
    
    # ═══════════════════════════════════════════════════════════════
    # VERIFICAR TIEMPO
    # ═══════════════════════════════════════════════════════════════
    
    if not verificar_tiempo():
        return False
    
    # ═══════════════════════════════════════════════════════════════
    # INICIALIZAR Y EJECUTAR
    # ═══════════════════════════════════════════════════════════════
    
    gestor = GestorRecetas()
    stats = gestor.historial.get('estadisticas', {})
    log(f"📊 Historial: {stats.get('total_publicadas', 0)} recetas publicadas previamente")
    
    # Seleccionar receta
    receta = seleccionar_receta(gestor)
    if not receta:
        return False
    
    # Construir contenido
    log(f"📝 Preparando contenido: {receta['nombre'][:50]}...")
    texto = construir_publicacion(receta)
    hashtags = generar_hashtags(receta)
    
    # Procesar imagen
    log("🖼️ Procesando imagen...")
    imagen_path = None
    
    if receta.get('imagen'):
        log(f"   ↳ URL imagen: {receta['imagen'][:60]}...", 'debug')
        imagen_path = descargar_imagen_receta(receta['imagen'])
    
    if not imagen_path:
        imagen_path = crear_imagen_receta(
            receta['nombre'],
            receta.get('categoria', 'Plato'),
            receta.get('area', 'Internacional')
        )
    
    if not imagen_path:
        log("❌ No se pudo obtener imagen", 'error')
        return False
    
    # Publicar
    exito = publicar_facebook(texto, imagen_path, hashtags)
    
    # Limpieza
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
            log(f"🗑️ Imagen temporal eliminada", 'debug')
    except:
        pass
    
    # Guardar estado
    if exito:
        gestor.guardar_receta(
            receta['id'],
            receta['nombre'],
            receta.get('categoria', 'General')
        )
        guardar_json(ESTADO_PATH, {'ultima_publicacion': datetime.now().isoformat()})
        log("🎉 ¡RECETA PUBLICADA EXITOSAMENTE!", 'exito')
        return True
    else:
        log("❌ Falló la publicación", 'error')
        return False

if __name__ == "__main__":
    try:
        exit_code = 0 if main() else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("🛑 Ejecución interrumpida por usuario", 'advertencia')
        sys.exit(130)
    except Exception as e:
        log(f"💥 Error crítico no manejado: {e}", 'error')
        import traceback
        traceback.print_exc()
        sys.exit(1)
