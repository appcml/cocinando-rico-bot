#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍳 Bot de Recetas TENDENCIA para Facebook - V3.0 VARIEDAD TOTAL
Recetas virales, saludables, comfort food, veganas, carnes, dulces, meal prep
"""

import requests
import json
import os
import re
import hashlib
import sys
import random
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import textwrap

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# APIs
EDAMAM_APP_ID = os.getenv('EDAMAM_APP_ID')
EDAMAM_API_KEY = os.getenv('EDAMAM_API_KEY')
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')  # Opcional
THEMEALDB_API = "https://www.themealdb.com/api/json/v1/1"

# Facebook
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
IMAGENES_TEMP = os.path.join(BASE_DIR, 'temp_img')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGENES_TEMP, exist_ok=True)

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', os.path.join(DATA_DIR, 'historial_recetas.json'))
ESTADO_PATH = os.getenv('ESTADO_PATH', os.path.join(DATA_DIR, 'estado_bot.json'))

# Tiempos
TIEMPO_ENTRE_PUBLICACIONES = int(os.getenv('TIEMPO_ENTRE_PUBLICACIONES', '240'))  # 4 horas
UMBRAL_SIMILITUD = 0.75
MAX_HISTORIAL = 200
MAX_IMAGENES = 4

# ═══════════════════════════════════════════════════════════════
# TENDENCIAS 2024-2025 - RECETAS VIRALES Y POPULARES
# ═══════════════════════════════════════════════════════════════

TENDENCIAS = {
    'virales_tiktok': [
        'pasta feta baked', 'salmon rice bowl', 'green goddess salad',
        'butter board', 'cloud bread', 'baked oats', 'feta pasta',
        'sushi bake', 'pizza bowl', 'tomato feta pasta'
    ],
    'comida_reconfortante': [
        'mac and cheese', 'lasagna', 'beef stew', 'chicken soup',
        'mashed potatoes', 'pot roast', 'meatloaf', 'chili con carne',
        'chicken pot pie', 'beef bourguignon'
    ],
    'saludables_rapidas': [
        ' Buddha bowl', 'grain bowl', 'smoothie bowl', 'protein bowl',
        'quinoa salad', 'chickpea salad', 'lentil soup', 'minestrone',
        'stuffed peppers', 'zucchini noodles'
    ],
    'carnes_asadas': [
        'brisket', 'pulled pork', 'ribs bbq', 'steak grill', 'roast beef',
        'lamb chops', 'pork tenderloin', 'beef tenderloin', 'prime rib',
        'chicken roast', 'turkey roast'
    ],
    'veganas_tendencia': [
        'cauliflower wings', 'jackfruit tacos', 'beyond burger',
        'vegan mac cheese', 'tofu scramble', 'tempeh bacon',
        'vegan lasagna', 'plant based steak', 'vegan sushi',
        'cashew cheese'
    ],
    'postres_virales': [
        'basque cheesecake', 'cookie skillet', 'brownie butter',
        'tiramisu easy', 'pavlova', 'creme brulee', 'chocolate lava cake',
        'banana bread', 'lemon bars', 'apple crumble'
    ],
    'meal_prep': [
        'meal prep chicken', 'meal prep bowls', 'freezer meals',
        'batch cooking', 'lunch prep', 'healthy meal prep',
        'protein prep', 'vegan meal prep', 'keto meal prep'
    ],
    'air_fryer': [
        'air fryer chicken', 'air fryer potatoes', 'air fryer vegetables',
        'air fryer fish', 'air fryer donuts', 'air fryer wings',
        'air fryer salmon', 'air fryer tofu'
    ],
    'internacional_fusion': [
        'korean bbq', 'sushi rolls', 'ramen homemade', 'pad thai',
        'butter chicken', 'tacos birria', 'poke bowl', 'bibimbap',
        'shawarma', 'falafel bowl'
    ],
    'desayunos_tendencia': [
        'avocado toast', 'shakshuka', 'pancakes fluffy', 'french toast',
        'breakfast burrito', 'eggs benedict', 'acai bowl', 'granola bowl',
        'breakfast bowl', 'smoked salmon bagel'
    ]
}

# Búsquedas en español para tendencias
BUSQUEDAS_ESPANOL_TENDENCIA = [
    # Virales traducidas
    "pasta feta horno", "bowl salmon arroz", "ensalada verde viral",
    "pan nube", "avena horneada", "sushi horneado",
    
    # Comfort food español
    "cocido madrileño", "fabada asturiana", "paella valenciana",
    "callos madrid", "rabo toro", "puchero andaluz",
    
    # Carnes españolas
    "chuletón asturiano", "cordero lechal", "cochinillo segovia",
    "presa iberica", "secreto iberico", "pluma pamplona",
    
    # Modernas españolas
    "tortilla patatas gourmet", "croquetas jamón ibérico",
    "pulpo gallega", "gambas ajillo", "pimientos padrón",
    
    # Fusion
    "tacos de carnitas", "burrito bowl", "poke bowl atun",
    "ramen casero", "dim sum", "bao buns",
    
    # Saludables español
    "ensalada quinoa", "bowl proteico", "tarta espinacas",
    "hummus casero", "tabulé", "falafel",
    
    # Dulces españoles
    "tarta santiago", "torrijas", "flan huevo", "natillas",
    "arroz leche", "crema catalana", "buñuelos viento",
    
    # Postres modernos
    "cheesecake oreo", "tarta red velvet", "brownie cookies",
    "galletas chocolate chips", "tiramisu casero", "panna cotta",
    
    # Meal prep español
    "tupper comida sana", "comida domingo semana", "batch cooking español",
    "congelar comida casera", "organizar comida semana"
]

# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ═══════════════════════════════════════════════════════════════

def log(mensaje, tipo='info'):
    iconos = {
        'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 
        'cocina': '👨‍🍳', 'viral': '🔥', 'tendencia': '📈', 'imagen': '📸',
        'proteina': '💪', 'dulce': '🍰', 'carne': '🥩', 'vegano': '🌱',
        'rapido': '⚡', 'comfort': '🍲', 'internacional': '🌍'
    }
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {iconos.get(tipo, 'ℹ️')} {mensaje}", flush=True)

def cargar_json_seguro(ruta, default=None):
    if default is None:
        default = {}
    if not os.path.exists(ruta):
        guardar_json(ruta, default)
        return default.copy()
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content or not content.strip():
                guardar_json(ruta, default)
                return default.copy()
            return json.loads(content)
    except:
        guardar_json(ruta, default)
        return default.copy()

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except:
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

def limpiar_temp():
    try:
        for f in os.listdir(IMAGENES_TEMP):
            os.remove(os.path.join(IMAGENES_TEMP, f))
    except:
        pass

# ═══════════════════════════════════════════════════════════════
# GESTIÓN DE RECETAS
# ═══════════════════════════════════════════════════════════════

class GestorRecetas:
    def __init__(self):
        self.historial = self.cargar_historial()
        
    def cargar_historial(self):
        default = {
            'ids_recetas': [],
            'urls': [],
            'hashes': [],
            'timestamps': [],
            'nombres': [],
            'categorias_tendencia': [],
            'estadisticas': {
                'total_publicadas': 0,
                'por_categoria': {}
            }
        }
        h = cargar_json_seguro(HISTORIAL_PATH, default)
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
                    if (ahora - fecha).days < 45:  # 45 días de historial
                        indices_mantener.append(i)
                except:
                    continue
            for key in ['ids_recetas', 'urls', 'hashes', 'timestamps', 'nombres', 'categorias_tendencia']:
                if key in h and isinstance(h[key], list):
                    h[key] = [h[key][i] for i in indices_mantener if i < len(h[key])]
        except:
            pass
    
    def receta_ya_publicada(self, id_receta, url, nombre):
        hash_nombre = generar_hash(nombre)
        
        if id_receta and id_receta in self.historial.get('ids_recetas', []):
            return True, "id_duplicado"
        
        if url and url in self.historial.get('urls', []):
            return True, "url_duplicada"
        
        if hash_nombre in self.historial.get('hashes', []):
            return True, "hash_duplicado"
        
        for nombre_hist in self.historial.get('nombres', []):
            sim = calcular_similitud(nombre, nombre_hist)
            if sim >= UMBRAL_SIMILITUD:
                return True, f"similitud_{sim:.2f}"
        
        return False, "nueva"
    
    def guardar_receta(self, id_receta, url, nombre, categoria_tendencia):
        hash_nombre = generar_hash(nombre)
        self.historial['ids_recetas'].append(id_receta or hash_nombre[:20])
        self.historial['urls'].append(url or "")
        self.historial['hashes'].append(hash_nombre)
        self.historial['timestamps'].append(datetime.now().isoformat())
        self.historial['nombres'].append(nombre)
        self.historial['categorias_tendencia'].append(categoria_tendencia)
        
        stats = self.historial.get('estadisticas', {})
        stats['total_publicadas'] = stats.get('total_publicadas', 0) + 1
        
        # Contar por categoría
        por_cat = stats.get('por_categoria', {})
        por_cat[categoria_tendencia] = por_cat.get(categoria_tendencia, 0) + 1
        stats['por_categoria'] = por_cat
        
        self.historial['estadisticas'] = stats
        
        # Limitar historial
        for key in ['ids_recetas', 'urls', 'hashes', 'timestamps', 'nombres', 'categorias_tendencia']:
            if len(self.historial[key]) > MAX_HISTORIAL:
                self.historial[key] = self.historial[key][-MAX_HISTORIAL:]
        
        guardar_json(HISTORIAL_PATH, self.historial)
        log(f"💾 Total: {stats['total_publicadas']} recetas", 'exito')

# ═══════════════════════════════════════════════════════════════
# SELECCIÓN INTELIGENTE DE TENDENCIA
# ═══════════════════════════════════════════════════════════════

def seleccionar_categoria_tendencia(gestor):
    """
    Selecciona categoría de tendencia basada en:
    1. Rotación (no repetir la misma)
    2. Popularidad actual
    3. Balance de contenido
    """
    stats = gestor.historial.get('estadisticas', {}).get('por_categoria', {})
    
    # Calcular pesos inversos (menos publicadas = más probabilidad)
    categorias = list(TENDENCIAS.keys())
    pesos = []
    
    for cat in categorias:
        count = stats.get(cat, 0)
        # Menos publicaciones = más peso, pero con algo de aleatoriedad
        peso = max(1, 10 - count) + random.randint(1, 5)
        pesos.append(peso)
    
    # Seleccionar con probabilidad ponderada
    total = sum(pesos)
    r = random.uniform(0, total)
    acumulado = 0
    
    for cat, peso in zip(categorias, pesos):
        acumulado += peso
        if r <= acumulado:
            return cat
    
    return random.choice(categorias)

def obtener_termino_busqueda(categoria_tendencia):
    """Obtiene término de búsqueda según tendencia"""
    if categoria_tendencia in TENDENCIAS:
        termino = random.choice(TENDENCIAS[categoria_tendencia])
        log(f"🔥 Tendencia: {categoria_tendencia} → '{termino}'", 'tendencia')
        return termino
    
    # Fallback a búsquedas en español
    termino = random.choice(BUSQUEDAS_ESPANOL_TENDENCIA)
    log(f"🇪🇸 Búsqueda español: '{termino}'", 'tendencia')
    return termino

# ═══════════════════════════════════════════════════════════════
# BÚSQUEDA DE RECETAS CON IMÁGENES
# ═══════════════════════════════════════════════════════════════

def buscar_receta_spoonacular(query):
    """Busca en Spoonacular (tendencias, imágenes HD)"""
    if not SPOONACULAR_API_KEY:
        return None
    
    try:
        url = "https://api.spoonacular.com/recipes/complexSearch"
        params = {
            'apiKey': SPOONACULAR_API_KEY,
            'query': query,
            'number': 5,
            'addRecipeInformation': True,
            'fillIngredients': True,
            'instructionsRequired': True,
            'sort': 'popularity',  # Ordenar por popularidad
            'sortDirection': 'desc'
        }
        
        response = requests.get(url, params=params, timeout=20)
        data = response.json()
        
        if response.status_code != 200 or not data.get('results'):
            return None
        
        # Seleccionar una popular
        receta_api = random.choice(data['results'])
        
        # Obtener detalles completos
        detalle_url = f"https://api.spoonacular.com/recipes/{receta_api['id']}/information"
        detalle_resp = requests.get(detalle_url, params={'apiKey': SPOONACULAR_API_KEY}, timeout=15)
        detalle = detalle_resp.json()
        
        if detalle_resp.status_code != 200:
            return None
        
        # Procesar ingredientes
        ingredientes = []
        for ing in detalle.get('extendedIngredients', []):
            texto = ing.get('original', '')
            if texto:
                ingredientes.append(texto)
        
        # Procesar instrucciones
        instrucciones = []
        for step in detalle.get('analyzedInstructions', [{}])[0].get('steps', []):
            instrucciones.append(step.get('step', ''))
        
        # Obtener imágenes adicionales si existen
        imagenes_extra = []
        # Spoonacular generalmente tiene una imagen principal de alta calidad
        
        receta = {
            'id': f"sp_{detalle['id']}",
            'nombre': detalle.get('title', 'Receta'),
            'imagen_principal': detalle.get('image'),
            'imagenes_extra': imagenes_extra,
            'url_fuente': detalle.get('sourceUrl', ''),
            'fuente': detalle.get('sourceName', 'Spoonacular'),
            'ingredientes': ingredientes,
            'instrucciones': instrucciones,
            'tiempo': detalle.get('readyInMinutes', 30),
            'porciones': detalle.get('servings', 4),
            'calorias': int(detalle.get('nutrition', {}).get('nutrients', [{}])[0].get('amount', 400)) if detalle.get('nutrition') else 400,
            'categoria': detalle.get('dishTypes', ['Plato'])[0] if detalle.get('dishTypes') else 'Plato',
            'tipo_cocina': detalle.get('cuisines', ['Internacional'])[0] if detalle.get('cuisines') else 'Internacional',
            'health_score': detalle.get('healthScore', 50),
            'popularidad': detalle.get('aggregateLikes', 0)
        }
        
        log(f"   ✅ {receta['nombre'][:50]} (❤️ {receta['popularidad']} likes)", 'exito')
        return receta
        
    except Exception as e:
        log(f"   ❌ Error Spoonacular: {e}", 'error')
        return None

def buscar_receta_edamam_tendencia(query):
    """Busca en Edamam con términos de tendencia"""
    if not EDAMAM_APP_ID or not EDAMAM_API_KEY:
        return None
    
    try:
        url = "https://api.edamam.com/api/recipes/v2"
        params = {
            'type': 'public',
            'q': query,
            'app_id': EDAMAM_APP_ID,
            'app_key': EDAMAM_API_KEY,
            'random': 'true',
            'imageSize': 'LARGE'
        }
        
        response = requests.get(url, params=params, timeout=20)
        data = response.json()
        
        if response.status_code != 200 or not data.get('hits'):
            return None
        
        # Filtrar recetas con buenas imágenes
        candidatas = []
        for hit in data['hits']:
            rec = hit.get('recipe', {})
            if rec.get('image') and len(rec.get('ingredientLines', [])) > 2:
                candidatas.append(rec)
        
        if not candidatas:
            return None
        
        receta_api = random.choice(candidatas)
        
        # Extraer datos
        receta = {
            'id': receta_api.get('uri', '').split('#recipe_')[-1],
            'nombre': receta_api.get('label', 'Receta'),
            'imagen_principal': receta_api.get('image'),
            'imagenes_extra': [],
            'url_fuente': receta_api.get('url', ''),
            'fuente': receta_api.get('source', 'Edamam'),
            'ingredientes': receta_api.get('ingredientLines', []),
            'instrucciones': [],  # Edamam no da instrucciones completas
            'tiempo': int(receta_api.get('totalTime', 0)) or 30,
            'porciones': int(receta_api.get('yield', 4)),
            'calorias': int(receta_api.get('calories', 0) / (receta_api.get('yield', 4) or 4)),
            'proteinas': int(receta_api.get('totalNutrients', {}).get('PROCNT', {}).get('quantity', 0) / (receta_api.get('yield', 4) or 4)),
            'categoria': receta_api.get('dishType', ['Plato'])[0] if receta_api.get('dishType') else 'Plato',
            'tipo_cocina': receta_api.get('cuisineType', ['Internacional'])[0] if receta_api.get('cuisineType') else 'Internacional',
            'dietas': receta_api.get('dietLabels', []),
            'saludable': receta_api.get('healthLabels', [])
        }
        
        # Generar instrucciones genéricas si no hay
        if not receta['instrucciones']:
            receta['instrucciones'] = generar_instrucciones_genericas(receta['ingredientes'])
        
        log(f"   ✅ {receta['nombre'][:50]}", 'exito')
        return receta
        
    except Exception as e:
        log(f"   ❌ Error Edamam: {e}", 'error')
        return None

def buscar_receta_themealdb_tendencia(query=None):
    """Backup: TheMealDB con imágenes garantizadas"""
    try:
        if query:
            # Buscar por nombre
            url = f"{THEMEALDB_API}/search.php?s={query}"
        else:
            # Aleatorio
            url = f"{THEMEALDB_API}/random.php"
        
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if not data or not data.get('meals'):
            return None
        
        meal = data['meals'][0] if query else random.choice(data['meals'])
        
        # Si buscamos específico y no encontramos, ir a aleatorio
        if query and not data.get('meals'):
            return buscar_receta_themealdb_tendencia(None)
        
        # Procesar
        ingredientes = []
        for i in range(1, 21):
            ing = meal.get(f'strIngredient{i}')
            med = meal.get(f'strMeasure{i}')
            if ing and ing.strip():
                ingredientes.append(f"{med} {ing}".strip() if med else ing)
        
        receta = {
            'id': f"mdb_{meal['idMeal']}",
            'nombre': meal.get('strMeal', 'Receta'),
            'imagen_principal': meal.get('strMealThumb'),
            'imagenes_extra': [],
            'url_fuente': meal.get('strSource') or f"https://www.themealdb.com/meal/{meal['idMeal']}",
            'fuente': 'TheMealDB',
            'ingredientes': ingredientes,
            'instrucciones': [meal.get('strInstructions', 'Sigue los pasos estándar.')],
            'tiempo': 30,
            'porciones': 4,
            'calorias': estimar_calorias(ingredientes),
            'categoria': meal.get('strCategory', 'Plato'),
            'tipo_cocina': meal.get('strArea', 'Internacional'),
            'video': meal.get('strYoutube', '')
        }
        
        log(f"   ✅ {receta['nombre'][:50]} [TheMealDB]", 'exito')
        return receta
        
    except Exception as e:
        log(f"   ❌ Error TheMealDB: {e}", 'error')
        return None

def generar_instrucciones_genericas(ingredientes):
    """Genera instrucciones básicas basadas en ingredientes"""
    pasos = [
        "Prepara todos los ingredientes lavando, picando y midiendo según sea necesario.",
        "Calienta una sartén grande o cacerola a fuego medio-alto con un poco de aceite.",
        "Agrega los ingredientes principales y cocina hasta que estén dorados o tiernos.",
        "Añade los condimentos y salsa. Mezcla bien para integrar sabores.",
        "Cocina a fuego lento durante el tiempo necesario hasta que esté listo.",
        "Sirve caliente y disfruta de tu preparación."
    ]
    return pasos

def estimar_calorias(ingredientes):
    """Estimación simple"""
    base = 300
    for ing in ingredientes:
        ing_lower = ing.lower()
        if any(x in ing_lower for x in ['carne', 'pollo', 'pescado', 'pasta', 'arroz']):
            base += 80
        elif any(x in ing_lower for x in ['mantequilla', 'aceite', 'queso', 'crema']):
            base += 60
    return min(base, 800)

# ═══════════════════════════════════════════════════════════════
# DESCARGA DE IMÁGENES REALES
# ═══════════════════════════════════════════════════════════════

def descargar_imagen_real(url, nombre_base, index=0):
    """Descarga imagen real desde URL con manejo de errores"""
    if not url:
        return None
    
    # Limpiar URL (eliminar parámetros de tracking)
    url_limpia = url.split('?')[0]
    
    try:
        log(f"   📥 Descargando imagen {index+1}...", 'imagen')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        }
        
        response = requests.get(url_limpia, headers=headers, timeout=25, stream=True)
        
        if response.status_code != 200:
            log(f"      ❌ HTTP {response.status_code}", 'error')
            return None
        
        # Verificar content-type
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type and 'octet-stream' not in content_type:
            log(f"      ⚠️ Content-Type: {content_type}", 'advertencia')
        
        img = Image.open(BytesIO(response.content))
        
        # Validar formato
        if img.format not in ['JPEG', 'JPG', 'PNG', 'WEBP', 'GIF']:
            log(f"      ❌ Formato: {img.format}", 'error')
            return None
        
        w, h = img.size
        if w < 300 or h < 200:
            log(f"      ❌ Muy pequeña: {w}x{h}", 'error')
            return None
        
        # Convertir a RGB
        if img.mode in ('RGBA', 'P', 'LA', 'L'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
                img = background
            else:
                img = img.convert('RGB')
        
        # Redimensionar para Facebook (óptimo 1200x630)
        if w > 1200 or h > 1200:
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        
        # Guardar
        path = os.path.join(IMAGENES_TEMP, f"{nombre_base}_{index}.jpg")
        img.save(path, 'JPEG', quality=92, optimize=True)
        
        size_kb = os.path.getsize(path) / 1024
        log(f"      ✅ {img.size[0]}x{img.size[1]} ({size_kb:.0f}KB)", 'exito')
        
        return path
        
    except Exception as e:
        log(f"      ❌ Error: {str(e)[:50]}", 'error')
        return None

def obtener_imagenes_receta(receta):
    """Obtiene todas las imágenes disponibles"""
    imagenes = []
    nombre_base = generar_hash(receta['nombre'])[:10]
    
    # Imagen principal
    if receta.get('imagen_principal'):
        img = descargar_imagen_real(receta['imagen_principal'], nombre_base, 0)
        if img:
            imagenes.append(img)
    
    # Imágenes extra
    for i, url in enumerate(receta.get('imagenes_extra', []), 1):
        if len(imagenes) >= MAX_IMAGENES:
            break
        img = descargar_imagen_real(url, nombre_base, i)
        if img:
            imagenes.append(img)
    
    # Si no hay imágenes, intentar con video thumbnail si existe
    if not imagenes and receta.get('video'):
        # Extraer ID de YouTube y usar thumbnail
        video_id = extract_youtube_id(receta['video'])
        if video_id:
            thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            img = descargar_imagen_real(thumb_url, nombre_base, 0)
            if img:
                imagenes.append(img)
    
    return imagenes

def extract_youtube_id(url):
    """Extrae ID de video de YouTube"""
    patterns = [
        r'v=([a-zA-Z0-9_-]{11})',
        r'youtu.be/([a-zA-Z0-9_-]{11})',
        r'embed/([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# ═══════════════════════════════════════════════════════════════
# GENERACIÓN DE CONTENIDO ADAPTABLE
# ═══════════════════════════════════════════════════════════════

def detectar_tipo_receta(receta):
    """Detecta el tipo de receta para adaptar el mensaje"""
    nombre = receta.get('nombre', '').lower()
    categoria = receta.get('categoria', '').lower()
    ingredientes = ' '.join(receta.get('ingredientes', [])).lower()
    
    # Detectar tipo
    if any(x in nombre or x in ingredientes for x in ['pollo', 'carne', 'res', 'cerdo', 'cordero', 'pavo']):
        if any(x in nombre for x in ['parrilla', 'asado', 'grill', 'bbq']):
            return 'parrilla', '🔥', 'ASADO PERFECTO'
        return 'carne', '🥩', 'PROTEÍNA DE CALIDAD'
    
    if any(x in nombre or x in ingredientes for x in ['pescado', 'salmón', 'atún', 'marisco', 'langostino']):
        return 'pescado', '🐟', 'FRESCO DEL MAR'
    
    if any(x in nombre for x in ['pasta', 'spaghetti', 'fettuccine', 'penne', 'macarrones']):
        return 'pasta', '🍝', 'AUTÉNTICA ITALIANA'
    
    if any(x in nombre for x in ['pizza', 'calzone', 'focaccia']):
        return 'pizza', '🍕', 'HORNO TRADICIONAL'
    
    if any(x in nombre or x in categoria for x in ['tarta', 'cake', 'cheesecake', 'brownie', 'galleta', 'muffin', 'donut']):
        return 'reposteria', '🍰', 'DULCE TENTACIÓN'
    
    if any(x in nombre for x in ['ensalada', 'bowl', 'poke', 'buddha']):
        return 'ensalada', '🥗', 'BOWL NUTRITIVO'
    
    if any(x in nombre or x in ingredientes for x in ['taco', 'burrito', 'nacho', 'quesadilla', 'fajita']):
        return 'mexicana', '🌮', 'SABOR MEXICANO'
    
    if any(x in nombre for x in ['sushi', 'ramen', 'poke', 'dumpling', 'bao']):
        return 'asiatica', '🍜', 'ORIENTE EN TU MESA'
    
    if any(x in nombre or x in ingredientes for x in ['vegan', 'tofu', 'tempeh', 'seitan', 'jackfruit']):
        return 'vegana', '🌱', 'PLANT BASED'
    
    if any(x in nombre for x in ['sopa', 'crema', 'guiso', 'estofado', 'cocido']):
        return 'sopa', '🍲', 'RECONFORTANTE'
    
    if any(x in nombre for x in ['desayuno', 'breakfast', 'pancake', 'waffle', 'tostada']):
        return 'desayuno', '🍳', 'BUENOS DÍAS'
    
    if any(x in nombre for x in ['sandwich', 'wrap', 'burger', 'panini', 'bagel']):
        return 'sandwich', '🥪', 'RÁPIDO Y RICO'
    
    return 'general', '👨‍🍳', 'RECETA ESPECIAL'

def formatear_ingredientes_chic(ingredientes, tipo):
    """Formatea ingredientes según el tipo de receta"""
    if not ingredientes:
        return "• Ingredientes frescos de calidad"
    
    lineas = []
    emojis_tipo = {
        'carne': '🥩', 'pescado': '🐟', 'pasta': '🍝', 'pizza': '🍕',
        'reposteria': '🧈', 'ensalada': '🥬', 'mexicana': '🌶️',
        'asiatica': '🥢', 'vegana': '🌿', 'sopa': '🥣',
        'desayuno': '🥚', 'sandwich': '🍞', 'parrilla': '🔥',
        'general': '•'
    }
    
    emoji_base = emojis_tipo.get(tipo, '•')
    
    for i, ing in enumerate(ingredientes[:10]):
        # Limpiar texto
        ing_limpio = re.sub(r'\s+', ' ', str(ing)).strip()
        if len(ing_limpio) > 40:
            ing_limpio = ing_limpio[:37] + "..."
        lineas.append(f"{emoji_base} {ing_limpio}")
    
    return '\n'.join(lineas)

def formatear_instrucciones_chic(instrucciones):
    """Formatea instrucciones elegantes"""
    if not instrucciones:
        return "Sigue tu intuición culinaria y disfruta del proceso. 👨‍🍳"
    
    if isinstance(instrucciones, list):
        pasos = instrucciones[:5]  # Máximo 5 pasos
    else:
        pasos = [instrucciones]
    
    formateados = []
    for i, paso in enumerate(pasos, 1):
        paso_limpio = str(paso).strip()
        # Limpiar números existentes
        paso_limpio = re.sub(r'^\d+[\.\)]\s*', '', paso_limpio)
        if len(paso_limpio) > 200:
            paso_limpio = paso_limpio[:197] + "..."
        formateados.append(f"👉 {paso_limpio}")
    
    return '\n\n'.join(formateados)

def construir_publicacion_tendencia(receta):
    """Construye publicación adaptada al tipo de receta"""
    tipo, emoji_tipo, badge = detectar_tipo_receta(receta)
    
    nombre = receta['nombre']
    tipo_cocina = receta.get('tipo_cocina', 'Internacional')
    tiempo = receta.get('tiempo', 30)
    porciones = receta.get('porciones', 4)
    
    # Formatear tiempo
    if tiempo > 60:
        tiempo_str = f"{tiempo//60}h {tiempo%60}min"
    else:
        tiempo_str = f"{tiempo} min"
    
    # Seleccionar mensaje según tipo
    mensajes_tipo = {
        'carne': [
            "Jugosa, llena de sabor y perfecta para los amantes de la buena carne. 🥩",
            "El corte perfecto, la cocción ideal. ¿Te atreves a probarla? 🔥",
            "Proteína de calidad para una comida que sacia de verdad. 💪"
        ],
        'pescado': [
            "Fresco del mar a tu mesa. Omega-3 y sabor incomparable. 🌊",
            "Ligero, saludable y delicioso. El mar en tu plato. 🐟",
            "La perfección del pescado bien cocinado. ¿Con limón o salsa? 🍋"
        ],
        'pasta': [
            "Auténtica tradición italiana. Al dente y llena de sabor. 🇮🇹",
            "El confort food por excelencia. ¿Con qué la acompañarías? 🍷",
            "Salsa, queso y pasta perfecta. Una combinación ganadora. 🧀"
        ],
        'reposteria': [
            "El dulce momento del día merece algo especial. ¿Te resistes? 🍰",
            "Aroma de horno y felicidad. Ideal para compartir. ☕",
            "Crujiente por fuera, suave por dentro. Perfección dulce. 🍯"
        ],
        'ensalada': [
            "Color, frescura y nutrientes. Comer sano nunca fue tan rico. 🌈",
            "Bowl lleno de vida. Tu cuerpo te lo agradecerá. ✨",
            "Ligera pero sustanciosa. Perfecta para cualquier momento. 🥑"
        ],
        'mexicana': [
            "Sabor, color y un toque picante. ¡Viva México! 🌶️",
            "Tortilla, guacamole y alegría. Fiesta en tu plato. 🎉",
            "Auténtico sabor latino. ¿Con salsa verde o roja? 🥑"
        ],
        'parrilla': [
            "El fuego hace magia. Jugosa, ahumada e irresistible. 🔥",
            "Domingo de asado vibes. ¿Quién se resiste? 🍖",
            "Carne perfectamente sellada. El arte de la parrilla. ♨️"
        ],
        'vegana': [
            "100% planta, 100% sabor. Sin sacrificios. 🌱",
            "Vegano y delicioso. ¿Quién dijo que era aburrido? 💚",
            "Ingredientes de la tierra, cocinados con amor. 🌍"
        ],
        'desayuno': [
            "Empieza el día con energía y buen sabor. ☀️",
            "El desayuno más importante del día, hecho especial. 🥞",
            "Mañanas que merecen algo así. ¿Con café o té? ☕"
        ],
        'sopa': [
            "Calor reconfortante para el alma. Bowl de felicidad. 🍲",
            "Ligera pero nutritiva. Perfecta para cualquier clima. 🥄",
            "Sabor casero que abraza. ¿Con pan tostado? 🍞"
        ]
    }
    
    mensaje_especifico = random.choice(mensajes_tipo.get(tipo, [
        "Receta que conquista por su sabor y presentación. ¿Te animas? 👨‍🍳",
        "Un clásico que nunca falla. Perfecto para cualquier ocasión. ⭐",
        "Sabor auténtico y preparación sencilla. Ideal para hoy. 🍽️"
    ]))
    
    lineas = [
        f"{emoji_tipo} {nombre}",
        "",
        f"🏷️ {badge} • {tipo_cocina}",
        f"⏱️ {tiempo_str} • 👤 {porciones} porciones",
        "",
        f"{mensaje_especifico}",
        "",
        "📝 INGREDIENTES:",
        formatear_ingredientes_chic(receta.get('ingredientes', []), tipo),
        "",
        "👨‍🍳 PREPARACIÓN:",
        formatear_instrucciones_chic(receta.get('instrucciones', [])),
        "",
        "─────────────────",
        "💡 TIP DEL CHEF:",
        "• Usa ingredientes frescos para mejor resultado.",
        "• Puedes guardar leftovers en tupper para mañana.",
        "• Ajusta especias a tu gusto personal.",
        "",
        "🔥 ¿La prepararás? Cuéntanos en comentarios 👇",
        "",
        "🍳 RECETAS QUE INSPIRAN",
        "Cocina con amor, come con alegría"
    ]
    
    return '\n'.join(lineas)

def generar_hashtags_tendencia(receta, tipo):
    """Hashtags virales y de tendencia"""
    hashtags_base = ['#Recetas', '#CocinaCasera', '#Foodie', '#InstaFood']
    
    hashtags_tipo = {
        'carne': ['#CarnePerfecta', '#Asado', '#Proteina', '#MeatLovers', '#Parrilla'],
        'pescado': ['#PescadoFresco', '#Mariscos', '#Omega3', '#Seafood', '#Healthy'],
        'pasta': ['#PastaLover', '#ItalianFood', '#ComfortFood', '#PastaTime', '#Spaghetti'],
        'pizza': ['#PizzaTime', '#HomemadePizza', '#PizzaLover', '#CheesePull'],
        'reposteria': ['#HomeBaking', '#SweetTooth', '#DessertLover', '#Pastry', '#Yummy'],
        'ensalada': ['#SaladBowl', '#HealthyEating', '#CleanEating', '#Nutritious', '#Fresh'],
        'mexicana': ['#MexicanFood', '#TacoTuesday', '#SpicyFood', '#LatinFood', '#Guacamole'],
        'asiatica': ['#AsianFood', '#SushiLover', '#Ramen', '#OrientalFood', '#Umami'],
        'vegana': ['#VeganFood', '#PlantBased', '#VeganRecipes', '#GreenFood', '#CrueltyFree'],
        'parrilla': ['#BBQ', '#GrillMaster', '#Asado', '#FireCooking', '#Smoke'],
        'desayuno': ['#BreakfastTime', '#MorningFuel', '#Brunch', '#Pancakes', '#GoodMorning'],
        'sopa': ['#SoupSeason', '#ComfortFood', '#WarmBowl', '#HomemadeSoup'],
        'sandwich': ['#SandwichLover', '#LunchTime', '#QuickMeal', '#StreetFood'],
        'general': ['#FoodLover', '#Delicious', '#Homemade', '#CookingTime']
    }
    
    # Añadir hashtags de tendencia actuales
    tendencias_virales = ['#FoodTok', '#RecipeOfTheDay', '#CookingAtHome', '#Yummy', '#Tasty']
    
    tipo_tags = hashtags_tipo.get(tipo, hashtags_tipo['general'])
    
    # Combinar y limitar
    todos = hashtags_base + tipo_tags + [random.choice(tendencias_virales)]
    
    return ' '.join(todos[:8])

# ═══════════════════════════════════════════════════════════════
# PUBLICACIÓN EN FACEBOOK
# ═══════════════════════════════════════════════════════════════

def publicar_facebook_tendencia(texto, imagenes_paths, receta):
    """Publica con múltiples imágenes y formato tendencia"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("❌ Facebook no configurado", 'error')
        return False
    
    tipo, _, _ = detectar_tipo_receta(receta)
    hashtags = generar_hashtags_tendencia(receta, tipo)
    mensaje = f"{texto}\n\n{hashtags}"
    
    # Truncar si necesario
    if len(mensaje) > 2200:
        partes = mensaje.split('─────────────────')
        if len(partes) > 1:
            mensaje = partes[0][:1700] + "\n\n[Continúa en comentarios...]\n\n" + partes[1]
    
    log(f"📘 Publicando {len(imagenes_paths)} imagen(es)...", 'facebook')
    
    try:
        if len(imagenes_paths) == 1:
            return publicar_simple(mensaje, imagenes_paths[0])
        else:
            return publicar_album(mensaje, imagenes_paths)
    except Exception as e:
        log(f"❌ Error: {e}", 'error')
        return False

def publicar_simple(mensaje, imagen_path):
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        with open(imagen_path, 'rb') as f:
            files = {'file': ('receta.jpg', f, 'image/jpeg')}
            data = {'message': mensaje, 'access_token': FB_ACCESS_TOKEN, 'published': 'true'}
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            if 'id' in result:
                log(f"   ✅ Publicada - ID: {result['id']}", 'exito')
                return True
            log(f"   ❌ {result.get('error', {})}", 'error')
            return False
    except Exception as e:
        log(f"   ❌ {e}", 'error')
        return False

def publicar_album(mensaje, imagenes_paths):
    try:
        # Subir imágenes sin publicar
        media_ids = []
        for i, img_path in enumerate(imagenes_paths):
            log(f"   📤 Subiendo {i+1}/{len(imagenes_paths)}...", 'facebook')
            url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
            with open(img_path, 'rb') as f:
                files = {'file': (f'img_{i}.jpg', f, 'image/jpeg')}
                data = {'published': 'false', 'access_token': FB_ACCESS_TOKEN}
                resp = requests.post(url, files=files, data=data, timeout=60)
                res = resp.json()
                if 'id' in res:
                    media_ids.append({'media_fbid': res['id']})
        
        if not media_ids:
            return False
        
        # Crear publicación con álbum
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
        data = {
            'message': mensaje,
            'attached_media': json.dumps(media_ids),
            'access_token': FB_ACCESS_TOKEN
        }
        response = requests.post(url, data=data, timeout=60)
        result = response.json()
        
        if 'id' in result:
            log(f"   ✅ ÁLBUM publicado - ID: {result['id']}", 'exito')
            return True
        
        # Fallback
        if media_ids:
            return publicar_simple(mensaje, imagenes_paths[0])
        return False
        
    except Exception as e:
        log(f"   ❌ {e}", 'error')
        return False

# ═══════════════════════════════════════════════════════════════
# FLUJO PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def verificar_tiempo():
    estado = cargar_json_seguro(ESTADO_PATH, {'ultima_publicacion': None})
    ultima = estado.get('ultima_publicacion')
    if not ultima:
        return True
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        minutos = (datetime.now() - ultima_dt).total_seconds() / 60
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {minutos:.0f}min", 'info')
            return False
        return True
    except:
        return True

def seleccionar_receta_tendencia(gestor):
    """Busca receta de tendencia con imágenes reales"""
    max_intentos = 20
    
    # Seleccionar categoría de tendencia
    categoria_tendencia = seleccionar_categoria_tendencia(gestor)
    termino_busqueda = obtener_termino_busqueda(categoria_tendencia)
    
    log(f"🔍 Buscando: '{termino_busqueda}'", 'tendencia')
    
    for intento in range(max_intentos):
        # Intentar Spoonacular primero (tendencias, imágenes HD)
        receta = buscar_receta_spoonacular(termino_busqueda)
        
        # Fallback a Edamam
        if not receta:
            receta = buscar_receta_edamam_tendencia(termino_busqueda)
        
        # Fallback a TheMealDB
        if not receta:
            receta = buscar_receta_themealdb_tendencia(termino_busqueda if random.random() > 0.5 else None)
        
        if not receta:
            # Cambiar término de búsqueda
            termino_busqueda = obtener_termino_busqueda(seleccionar_categoria_tendencia(gestor))
            continue
        
        # Verificar duplicados
        es_dup, razon = gestor.receta_ya_publicada(
            receta.get('id'),
            receta.get('url_fuente'),
            receta['nombre']
        )
        
        if es_dup:
            log(f"   ↳ Ya publicada", 'debug')
            continue
        
        # Verificar que tenga imagen
        if not receta.get('imagen_principal'):
            log(f"   ⚠️ Sin imagen", 'advertencia')
            continue
        
        log(f"   ✅ {receta['nombre'][:50]}", 'exito')
        return receta, categoria_tendencia
    
    log("❌ No se encontró receta", 'error')
    return None, None

def main():
    print("\n" + "="*70)
    print("🔥 RECETAS TENDENCIA BOT - V3.0 VARIEDAD TOTAL")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Validaciones
    errores = []
    if not FB_PAGE_ID or FB_PAGE_ID == 'tu_page_id_aqui':
        errores.append("FB_PAGE_ID")
    if not FB_ACCESS_TOKEN or FB_ACCESS_TOKEN == 'tu_token_de_acceso_aqui':
        errores.append("FB_ACCESS_TOKEN")
    
    if errores:
        log("❌ Faltan: " + ", ".join(errores), 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    limpiar_temp()
    
    gestor = GestorRecetas()
    stats = gestor.historial.get('estadisticas', {})
    log(f"📊 Publicadas: {stats.get('total_publicadas', 0)} recetas", 'info')
    
    # Mostrar distribución por categoría
    por_cat = stats.get('por_categoria', {})
    if por_cat:
        log("📈 Distribución:", 'info')
        for cat, count in sorted(por_cat.items(), key=lambda x: x[1], reverse=True)[:5]:
            log(f"   • {cat}: {count}", 'info')
    
    # Buscar receta
    receta, categoria_tendencia = seleccionar_receta_tendencia(gestor)
    if not receta:
        return False
    
    # Descargar imágenes
    log("📸 Descargando imágenes reales...")
    imagenes = obtener_imagenes_receta(receta)
    
    if not imagenes:
        log("❌ Sin imágenes", 'error')
        return False
    
    log(f"   📷 {len(imagenes)} imagen(es) lista(s)", 'exito')
    
    # Preparar y publicar
    texto = construir_publicacion_tendencia(receta)
    exito = publicar_facebook_tendencia(texto, imagenes, receta)
    
    if exito:
        gestor.guardar_receta(
            receta.get('id'),
            receta.get('url_fuente', ''),
            receta['nombre'],
            categoria_tendencia
        )
        guardar_json(ESTADO_PATH, {'ultima_publicacion': datetime.now().isoformat()})
        log("🎉 ¡RECETA TENDENCIA PUBLICADA!", 'exito')
        return True
    
    log("❌ Falló", 'error')
    return False

if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        log(f"💥 Error: {e}", 'error')
        import traceback
        traceback.print_exc()
        sys.exit(1)
