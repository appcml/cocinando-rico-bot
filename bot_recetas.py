#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🥗 Bot de Recetas FITNESS & SALUDABLE para Facebook - V2.0
Recetas en español: proteicas, dietas, asados, saludable
"""

import requests
import json
import os
import re
import hashlib
import sys
import random
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from PIL import Image, ImageDraw, ImageFont
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
THEMEALDB_API = "https://www.themealdb.com/api/json/v1/1"
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')  # Opcional, para más recetas

# Facebook
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', os.path.join(DATA_DIR, 'historial_recetas.json'))
ESTADO_PATH = os.getenv('ESTADO_PATH', os.path.join(DATA_DIR, 'estado_bot.json'))

# Tiempos
TIEMPO_ENTRE_PUBLICACIONES = int(os.getenv('TIEMPO_ENTRE_PUBLICACIONES', '360'))  # 6 horas
UMBRAL_SIMILITUD = 0.75
MAX_HISTORIAL = 100

# ═══════════════════════════════════════════════════════════════
# CATEGORÍAS FITNESS/SALUDABLE EN ESPAÑOL
# ═══════════════════════════════════════════════════════════════

CATEGORIAS_FITNESS = {
    'proteicas': ['Beef', 'Chicken', 'Lamb', 'Pork', 'Seafood', 'Goat'],
    'saludables': ['Vegetarian', 'Vegan', 'Salad', 'Side'],
    'bajas_calorias': ['Seafood', 'Chicken', 'Vegetarian'],
    'asados': ['Beef', 'Chicken', 'Lamb', 'Pork'],
    'postres_saludables': ['Dessert']  # Ocasional
}

PALABRAS_CLAVE_PROTEICAS = [
    'pollo', 'carne', 'res', 'cerdo', 'cordero', 'pescado', 'marisco',
    'huevo', 'proteina', 'proteico', 'asado', 'parrilla', 'filete',
    'pechuga', 'musculo', 'fitness', 'gym', 'entrenamiento'
]

PALABRAS_CLAVE_SALUDABLES = [
    'ensalada', 'verdura', 'vegetal', 'dieta', 'light', 'bajo caloria',
    'nutritivo', 'saludable', 'fit', 'natural', 'organico', 'integral'
]

# ═══════════════════════════════════════════════════════════════
# TRADUCCIONES DE INGREDIENTES Y TÉRMINOS
# ═══════════════════════════════════════════════════════════════

TRADUCCIONES_INGREDIENTES = {
    'chicken': 'pollo', 'beef': 'carne de res', 'pork': 'cerdo',
    'lamb': 'cordero', 'fish': 'pescado', 'salmon': 'salmón',
    'rice': 'arroz', 'pasta': 'pasta', 'potato': 'papa',
    'tomato': 'tomate', 'onion': 'cebolla', 'garlic': 'ajo',
    'oil': 'aceite', 'salt': 'sal', 'pepper': 'pimienta',
    'cheese': 'queso', 'milk': 'leche', 'butter': 'mantequilla',
    'egg': 'huevo', 'flour': 'harina', 'sugar': 'azúcar',
    'water': 'agua', 'wine': 'vino', 'lemon': 'limón',
    'herbs': 'hierbas', 'spices': 'especias', 'yogurt': 'yogur',
    'cream': 'crema', 'sauce': 'salsa', 'broth': 'caldo',
    'stock': 'caldo', 'grilled': 'a la parrilla', 'baked': 'horneado',
    'fried': 'frito', 'roasted': 'asado', 'steamed': 'al vapor',
    'fresh': 'fresco', 'dried': 'seco', 'chopped': 'picado',
    'sliced': 'en láminas', 'minced': 'picado fino', 'ground': 'molido'
}

TRADUCCIONES_CATEGORIAS = {
    'Beef': 'Carne de Res 🥩',
    'Chicken': 'Pollo Proteico 🍗',
    'Dessert': 'Postre Saludable 🍮',
    'Lamb': 'Cordero 🍖',
    'Miscellaneous': 'Variedad 🍽️',
    'Pasta': 'Pasta Integral 🍝',
    'Pork': 'Cerdo 🥓',
    'Seafood': 'Mariscos Proteicos 🦐',
    'Side': 'Acompañamiento Saludable 🥗',
    'Starter': 'Entrada Light 🥙',
    'Vegan': 'Vegano Fitness 🌱',
    'Vegetarian': 'Vegetariano Proteico 🥬',
    'Breakfast': 'Desayuno Energético 🍳',
    'Goat': 'Cabra 🐐',
    'Salad': 'Ensalada Nutritiva 🥗'
}

TRADUCCIONES_AREAS = {
    'American': 'Americana 🇺🇸',
    'British': 'Británica 🇬🇧',
    'Canadian': 'Canadiense 🇨🇦',
    'Chinese': 'China 🇨🇳',
    'Croatian': 'Croata 🇭🇷',
    'Dutch': 'Holandesa 🇳🇱',
    'Egyptian': 'Egipcia 🇪🇬',
    'Filipino': 'Filipina 🇵🇭',
    'French': 'Francesa 🇫🇷',
    'Greek': 'Griega 🇬🇷',
    'Indian': 'India 🇮🇳',
    'Irish': 'Irlandesa 🇮🇪',
    'Italian': 'Italiana 🇮🇹',
    'Jamaican': 'Jamaicana 🇯🇲',
    'Japanese': 'Japonesa 🇯🇵',
    'Kenyan': 'Keniana 🇰🇪',
    'Malaysian': 'Malaya 🇲🇾',
    'Mexican': 'Mexicana 🇲🇽',
    'Moroccan': 'Marroquí 🇲🇦',
    'Polish': 'Polaca 🇵🇱',
    'Portuguese': 'Portuguesa 🇵🇹',
    'Russian': 'Rusa 🇷🇺',
    'Spanish': 'Española 🇪🇸',
    'Thai': 'Tailandesa 🇹🇭',
    'Tunisian': 'Tunecina 🇹🇳',
    'Turkish': 'Turca 🇹🇷',
    'Ukrainian': 'Ucraniana 🇺🇦',
    'Vietnamese': 'Vietnamita 🇻🇳'
}

# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ═══════════════════════════════════════════════════════════════

def log(mensaje, tipo='info'):
    iconos = {
        'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 
        'cocina': '👨‍🍳', 'debug': '🔍', 'facebook': '📘', 'api': '🌐',
        'proteina': '💪', 'salud': '🥗'
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

# ═══════════════════════════════════════════════════════════════
# TRADUCTOR AUTOMÁTICO
# ═══════════════════════════════════════════════════════════════

def traducir_texto(texto_ingles):
    """Traduce texto básico de inglés a español"""
    if not texto_ingles:
        return ""
    
    texto = texto_ingles.lower()
    
    # Reemplazar ingredientes comunes
    for ingles, espanol in TRADUCCIONES_INGREDIENTES.items():
        texto = re.sub(r'\b' + ingles + r'\b', espanol, texto)
    
    # Reemplazar términos de cocción
    texto = texto.replace('grilled', 'a la parrilla')
    texto = texto.replace('baked', 'horneado')
    texto = texto.replace('fried', 'frito')
    texto = texto.replace('roasted', 'asado')
    texto = texto.replace('steamed', 'al vapor')
    texto = texto.replace('fresh', 'fresco')
    texto = texto.replace('chopped', 'picado')
    texto = texto.replace('minced', 'picado fino')
    texto = texto.replace('sliced', 'en láminas')
    
    # Capitalizar primera letra
    texto = texto.capitalize()
    
    return texto

def traducir_categoria(categoria_en):
    return TRADUCCIONES_CATEGORIAS.get(categoria_en, categoria_en)

def traducir_area(area_en):
    return TRADUCCIONES_AREAS.get(area_en, area_en)

def traducir_ingrediente(nombre_ing):
    nombre_lower = nombre_ing.lower()
    for ingles, espanol in TRADUCCIONES_INGREDIENTES.items():
        if ingles in nombre_lower:
            return nombre_ing.replace(ingles, espanol).replace(ingles.capitalize(), espanol.capitalize())
    return nombre_ing

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
                    if (ahora - fecha).days < 30:
                        indices_mantener.append(i)
                except:
                    continue
            for key in ['ids_recetas', 'hashes', 'timestamps', 'nombres', 'categorias']:
                if key in h and isinstance(h[key], list):
                    h[key] = [h[key][i] for i in indices_mantener if i < len(h[key])]
        except:
            pass
    
    def receta_ya_publicada(self, id_receta, nombre):
        hash_nombre = generar_hash(nombre)
        if id_receta in self.historial.get('ids_recetas', []):
            return True, "id_duplicado"
        if hash_nombre in self.historial.get('hashes', []):
            return True, "hash_duplicado"
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
        stats = self.historial.get('estadisticas', {})
        stats['total_publicadas'] = stats.get('total_publicadas', 0) + 1
        self.historial['estadisticas'] = stats
        for key in ['ids_recetas', 'hashes', 'timestamps', 'nombres', 'categorias']:
            if len(self.historial[key]) > MAX_HISTORIAL:
                self.historial[key] = self.historial[key][-MAX_HISTORIAL:]
        guardar_json(HISTORIAL_PATH, self.historial)
        log(f"💾 Total: {stats['total_publicadas']} recetas", 'exito')

# ═══════════════════════════════════════════════════════════════
# OBTENCIÓN DE RECETAS - ENFOQUE FITNESS
# ═══════════════════════════════════════════════════════════════

def obtener_receta_fitness():
    """Obtiene receta enfocada en proteínas y saludable"""
    # Priorizar categorías proteicas
    categorias_prioridad = ['Beef', 'Chicken', 'Seafood', 'Lamb', 'Pork']
    
    for categoria in categorias_prioridad:
        receta = obtener_receta_por_categoria(categoria)
        if receta:
            log(f"   💪 Receta proteica encontrada: {categoria}", 'proteina')
            return receta
    
    # Si no hay proteicas, buscar cualquiera
    return obtener_receta_aleatoria()

def obtener_receta_aleatoria():
    try:
        log("🌐 TheMealDB...", 'api')
        url = f"{THEMEALDB_API}/random.php"
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        data = response.json()
        if not data or not data.get('meals'):
            return None
        receta = procesar_receta_themealdb(data['meals'][0])
        log(f"   ✅ {receta['nombre'][:50]}", 'exito')
        return receta
    except Exception as e:
        log(f"   ❌ Error: {e}", 'error')
        return None

def obtener_receta_por_categoria(categoria):
    try:
        url = f"{THEMEALDB_API}/filter.php?c={categoria}"
        response = requests.get(url, timeout=15)
        data = response.json()
        if not data or not data.get('meals'):
            return None
        receta_basica = random.choice(data['meals'])
        return obtener_detalles_receta(receta_basica['idMeal'])
    except Exception as e:
        log(f"Error cat {categoria}: {e}", 'error')
        return None

def obtener_detalles_receta(id_receta):
    try:
        url = f"{THEMEALDB_API}/lookup.php?i={id_receta}"
        response = requests.get(url, timeout=15)
        data = response.json()
        if data and data.get('meals'):
            return procesar_receta_themealdb(data['meals'][0])
        return None
    except Exception as e:
        log(f"Error detalles: {e}", 'error')
        return None

def procesar_receta_themealdb(datos):
    receta = {
        'id': datos.get('idMeal'),
        'nombre': traducir_texto(datos.get('strMeal', 'Receta Fitness')),
        'categoria': datos.get('strCategory', 'Plato'),
        'area': datos.get('strArea', 'Internacional'),
        'instrucciones': datos.get('strInstructions', ''),
        'imagen': datos.get('strMealThumb'),
        'video': datos.get('strYoutube', ''),
        'fuente': datos.get('strSource') or 'TheMealDB',
        'ingredientes': []
    }
    
    for i in range(1, 21):
        ingrediente = datos.get(f'strIngredient{i}')
        medida = datos.get(f'strMeasure{i}')
        if ingrediente and str(ingrediente).strip():
            nombre_esp = traducir_ingrediente(str(ingrediente).strip())
            receta['ingredientes'].append({
                'nombre': nombre_esp,
                'cantidad': str(medida).strip() if medida else 'al gusto'
            })
    
    return receta

# ═══════════════════════════════════════════════════════════════
# GENERACIÓN DE CONTENIDO EN ESPAÑOL
# ═══════════════════════════════════════════════════════════════

def formatear_ingredientes(ingredientes):
    if not ingredientes:
        return "• Ingredientes no disponibles"
    
    lineas = []
    for ing in ingredientes[:12]:
        cantidad = ing.get('cantidad', '')
        nombre = ing.get('nombre', '')
        emoji = obtener_emoji_ingrediente(nombre)
        
        if cantidad and cantidad.lower() != 'al gusto':
            lineas.append(f"{emoji} {cantidad} {nombre}")
        else:
            lineas.append(f"{emoji} {nombre}")
    
    return '\n'.join(lineas)

def obtener_emoji_ingrediente(ingrediente):
    ingrediente_lower = ingrediente.lower()
    emojis = {
        'pollo': '🍗', 'carne': '🥩', 'res': '🥩', 'cerdo': '🥓',
        'cordero': '🍖', 'pescado': '🐟', 'salmón': '🐟', 'atún': '🐟',
        'huevo': '🥚', 'huevo': '🥚', 'proteina': '💪',
        'arroz': '🍚', 'pasta': '🍝', 'papa': '🥔', 'patata': '🥔',
        'tomate': '🍅', 'cebolla': '🧅', 'ajo': '🧄',
        'aceite': '🛢️', 'sal': '🧂', 'pimienta': '🌶️',
        'queso': '🧀', 'leche': '🥛', 'mantequilla': '🧈',
        'harina': '🌾', 'azúcar': '🍬', 'agua': '💧',
        'vino': '🍷', 'limón': '🍋', 'limon': '🍋',
        'yogur': '🥣', 'yogurt': '🥣', 'crema': '🥛',
        'ensalada': '🥗', 'verdura': '🥬', 'vegetal': '🥕',
        'pollo': '🍗', 'pechuga': '🍗', 'filete': '🥩',
        'parrilla': '🔥', 'asado': '🔥', 'horno': '♨️',
        'default': '•'
    }
    
    for key, emoji in emojis.items():
        if key in ingrediente_lower:
            return emoji
    return emojis['default']

def formatear_instrucciones(instrucciones):
    if not instrucciones:
        return "Instrucciones no disponibles."
    
    # Traducir instrucciones básicas
    texto = instrucciones.replace('\r', '\n').strip()
    
    # Dividir en pasos
    pasos = []
    lineas = [l.strip() for l in texto.split('\n') if l.strip() and len(l.strip()) > 20]
    
    for linea in lineas:
        linea_limpia = re.sub(r'^\d+[\.\)]\s*', '', linea)
        # Traducir términos comunes
        linea_limpia = traducir_texto(linea_limpia)
        if len(linea_limpia) > 20:
            pasos.append(linea_limpia)
    
    if len(pasos) < 2:
        oraciones = [o.strip() for o in texto.split('.') if len(o.strip()) > 30]
        pasos = [traducir_texto(o) for o in oraciones]
    
    pasos_formateados = []
    for i, paso in enumerate(pasos[:5], 1):
        if len(paso) > 200:
            paso = paso[:197] + "..."
        pasos_formateados.append(f"{i}. {paso}")
    
    return '\n\n'.join(pasos_formateados)

def construir_publicacion(receta):
    nombre = receta['nombre']
    categoria = traducir_categoria(receta.get('categoria', 'Plato'))
    area = traducir_area(receta.get('area', 'Internacional'))
    
    # Calcular proteínas estimadas (simple)
    proteinas_estimadas = estimar_proteinas(receta)
    
    lineas = [
        f"💪 {nombre}",
        "",
        f"📍 {area} • {categoria}",
        f"🥩 Proteínas estimadas: ~{proteinas_estimadas}g",
        "",
        "📝 INGREDIENTES:",
        formatear_ingredientes(receta.get('ingredientes', [])),
        "",
        "👨‍🍳 PREPARACIÓN:",
        formatear_instrucciones(receta.get('instrucciones', '')),
        "",
        "─────────────────",
        "💡 Tip Fitness: Ideal para ganar masa muscular 💪",
        "🔥 Comparte si te gusta esta receta proteica",
    ]
    
    if receta.get('fuente') and receta['fuente'] != 'TheMealDB':
        lineas.append(f"")
        lineas.append(f"🔗 {receta['fuente']}")
    
    return '\n'.join(lineas)

def estimar_proteinas(receta):
    """Estima proteínas basado en ingredientes principales"""
    ingredientes = receta.get('ingredientes', [])
    proteinas = 0
    
    proteicos = {
        'pollo': 25, 'carne': 26, 'res': 26, 'cerdo': 25, 'cordero': 25,
        'pescado': 22, 'salmón': 20, 'atún': 30, 'huevo': 13,
        'queso': 25, 'yogur': 10, 'leche': 8
    }
    
    for ing in ingredientes:
        nombre = ing.get('nombre', '').lower()
        for prot, cantidad in proteicos.items():
            if prot in nombre:
                proteinas += cantidad
                break
    
    return max(proteinas, 15)  # Mínimo 15g

def generar_hashtags(receta):
    categoria = receta.get('categoria', '').lower()
    area = receta.get('area', '').lower()
    nombre = receta.get('nombre', '').lower()
    
    # Hashtags base fitness
    hashtags = [
        '#CocinaFitness', '#ComidaSaludable', '#RecetasProteicas',
        '#Fitness', '#Gym', '#Proteina', '#ComidaFit'
    ]
    
    # Hashtags por tipo
    if any(p in categoria for p in ['beef', 'chicken', 'lamb', 'pork', 'goat']):
        hashtags.extend(['#CarneProteica', '#Musculo', '#GanarMasa', '#Asado', '#Parrilla'])
    elif any(p in categoria for p in ['seafood', 'fish']):
        hashtags.extend(['#PescadoProteico', '#Omega3', '#Saludable'])
    elif any(p in categoria for p in ['vegetarian', 'vegan']):
        hashtags.extend(['#VegetarianoFit', '#PlantBased', '#VeganProtein'])
    else:
        hashtags.extend(['#RecetaFit', '#Dieta', '#Nutricion'])
    
    # Hashtags por área
    areas_fit = {
        'italian': '#CocinaItalianaFit',
        'mexican': '#ComidaMexicanaFit',
        'spanish': '#CocinaEspañolaFit',
        'american': '#FitnessUSA',
        'asian': '#ComidaAsiaticaFit'
    }
    
    for key, tag in areas_fit.items():
        if key in area:
            hashtags.append(tag)
            break
    
    return ' '.join(hashtags[:8])  # Máximo 8 hashtags para no saturar

# ═══════════════════════════════════════════════════════════════
# IMÁGENES
# ═══════════════════════════════════════════════════════════════

def descargar_imagen_receta(url_imagen):
    if not url_imagen:
        return None
    
    if not url_imagen.startswith(('http://', 'https://')):
        return None
    
    try:
        from io import BytesIO
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url_imagen, headers=headers, timeout=20, stream=True)
        
        if response.status_code != 200:
            return None
        
        img = Image.open(BytesIO(response.content))
        
        if img.format not in ['JPEG', 'JPG', 'PNG', 'GIF', 'WEBP']:
            return None
        
        w, h = img.size
        if w < 200 or h < 200:
            return None
        
        if img.mode in ('RGBA', 'P', 'LA', 'L'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
                img = background
            else:
                img = img.convert('RGB')
        
        max_size = (1200, 1200)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        w, h = img.size
        ratio = w / h
        if ratio > 3 or ratio < 0.3:
            new_size = max(w, h)
            new_img = Image.new('RGB', (new_size, new_size), (255, 255, 255))
            x = (new_size - w) // 2
            y = (new_size - h) // 2
            new_img.paste(img, (x, y))
            img = new_img
        
        hash_img = generar_hash(url_imagen)[:10]
        path = os.path.join('/tmp', f'receta_{hash_img}.jpg')
        img.save(path, 'JPEG', quality=85, optimize=True)
        
        if os.path.getsize(path) > 8 * 1024 * 1024:
            img.save(path, 'JPEG', quality=70, optimize=True)
        
        return path
        
    except Exception as e:
        log(f"Error imagen: {e}", 'error')
        return None

def crear_imagen_receta(nombre_receta, categoria, area):
    try:
        # Paletas fitness
        paletas = {
            'Beef': ('#8B0000', '#FF6B6B', '#FFE0E0'),      # Rojo intenso
            'Chicken': ('#FFA500', '#FFD93D', '#FFF5E0'),    # Naranja energía
            'Seafood': ('#1E3A5F', '#4ECDC4', '#E0F7FA'),    # Azul oceano
            'Lamb': ('#800080', '#DA70D6', '#F0E0F0'),      # Púrpura
            'Pork': ('#FF69B4', '#FFB6C1', '#FFF0F5'),      # Rosa
            'Vegetarian': ('#228B22', '#90EE90', '#F0FFF0'), # Verde salud
            'Vegan': ('#2E8B57', '#98FB98', '#F5FFFA'),
            'Dessert': ('#8B4513', '#D2691E', '#F5E6D3'),   # Marrón
        }
        
        bg_color, accent_color, text_bg = paletas.get(categoria, ('#2C3E50', '#E74C3C', '#ECF0F1'))
        
        img = Image.new('RGB', (1200, 630), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        except:
            font_title = font_sub = font_small = ImageFont.load_default()
        
        # Barra superior
        draw.rectangle([(0, 0), (1200, 12)], fill=accent_color)
        
        # Área de texto
        draw.rectangle([(50, 140), (1150, 490)], fill=text_bg)
        
        # Título
        titulo = textwrap.fill(nombre_receta[:70], width=30)
        draw.text((100, 180), titulo, font=font_title, fill='#2C3E50')
        
        # Info
        info = f"💪 {area} • {categoria}"
        draw.text((100, 380), info, font=font_sub, fill=bg_color)
        
        # Proteínas badge
        draw.rectangle([(100, 430), (400, 470)], fill=accent_color)
        draw.text((250, 450), "ALTO EN PROTEÍNAS", font=font_small, fill='white', anchor="mm")
        
        # Footer
        draw.rectangle([(0, 580), (1200, 630)], fill='#2C3E50')
        draw.text((600, 605), "🔥 Cocina Fitness | Recetas Proteicas", 
                 font=font_small, fill='white', anchor="mm")
        
        hash_nombre = generar_hash(nombre_receta)[:10]
        path = os.path.join('/tmp', f'receta_gen_{hash_nombre}.jpg')
        img.save(path, 'JPEG', quality=90, optimize=True)
        
        return path
        
    except Exception as e:
        log(f"Error creando imagen: {e}", 'error')
        return None

# ═══════════════════════════════════════════════════════════════
# FACEBOOK
# ═══════════════════════════════════════════════════════════════

def publicar_facebook(texto, imagen_path, hashtags):
    if not FB_PAGE_ID or FB_PAGE_ID == 'tu_page_id_aqui':
        log("❌ FB_PAGE_ID no configurado", 'error')
        return False
    
    if not FB_ACCESS_TOKEN or FB_ACCESS_TOKEN == 'tu_token_de_acceso_aqui':
        log("❌ FB_ACCESS_TOKEN no configurado", 'error')
        return False
    
    log(f"📘 Publicando...", 'facebook')
    
    mensaje = f"{texto}\n\n{hashtags}\n\n— 💪 Cocina Fitness | Recetas Proteicas para tu Entrenamiento"
    
    if len(mensaje) > 2200:
        lineas = texto.split('\n')
        texto_cortado = ""
        for linea in lineas:
            if len(texto_cortado + linea + "\n") < 1800:
                texto_cortado += linea + "\n"
            else:
                break
        mensaje = f"{texto_cortado.rstrip()}\n\n[Ver receta completa]\n\n{hashtags}\n\n— 💪 Cocina Fitness"
    
    if not os.path.exists(imagen_path):
        log(f"❌ Imagen no existe", 'error')
        return False
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            files = {'file': ('receta.jpg', f, 'image/jpeg')}
            data = {'message': mensaje, 'access_token': FB_ACCESS_TOKEN, 'published': 'true'}
            
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            if 'id' in result:
                log(f"✅ PUBLICADO - ID: {result['id']}", 'exito')
                return True
            else:
                error = result.get('error', {})
                log(f"❌ Error {error.get('code')}: {error.get('message')}", 'error')
                return False
                
    except Exception as e:
        log(f"❌ Error: {e}", 'error')
        return False

# ═══════════════════════════════════════════════════════════════
# FLUJO PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def verificar_tiempo():
    estado = cargar_json_seguro(ESTADO_PATH, {'ultima_publicacion': None})
    ultima = estado.get('ultima_publicacion')
    
    if not ultima:
        log("📝 Primera ejecución", 'info')
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        minutos = (datetime.now() - ultima_dt).total_seconds() / 60
        
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {minutos:.0f}min", 'info')
            return False
        else:
            log(f"⏱️ Tiempo OK: {minutos:.0f}min", 'info')
            return True
    except:
        return True

def seleccionar_receta(gestor):
    """Selecciona receta enfocada en fitness/proteínas"""
    max_intentos = 25
    
    log(f"🔍 Buscando receta FITNESS...", 'proteina')
    
    for intento in range(max_intentos):
        # 70% probabilidad de receta proteica
        if random.random() < 0.7:
            receta = obtener_receta_fitness()
        else:
            receta = obtener_receta_aleatoria()
        
        if not receta:
            continue
        
        id_receta = receta.get('id')
        nombre = receta.get('nombre')
        
        if not id_receta or not nombre:
            continue
        
        es_dup, razon = gestor.receta_ya_publicada(id_receta, nombre)
        if es_dup:
            log(f"   ↳ Duplicado: {nombre[:40]}...", 'debug')
            continue
        
        if len(receta.get('ingredientes', [])) < 2:
            continue
        
        # Verificar que sea proteica o saludable
        categoria = receta.get('categoria', '').lower()
        es_proteica = any(p in categoria for p in ['beef', 'chicken', 'seafood', 'lamb', 'pork'])
        
        if es_proteica:
            log(f"   💪 RECETA PROTEICA: {nombre}", 'exito')
        else:
            log(f"   🥗 Receta saludable: {nombre}", 'exito')
        
        return receta
    
    log("❌ No se encontró receta", 'error')
    return None

def main():
    print("\n" + "="*70)
    print("💪 COCINA FITNESS BOT - V2.0")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Validaciones
    errores = []
    
    if sys.version_info < (3, 7):
        errores.append("Python 3.7+ requerido")
    
    if not FB_PAGE_ID or FB_PAGE_ID == 'tu_page_id_aqui':
        errores.append("FB_PAGE_ID no configurado")
    
    if not FB_ACCESS_TOKEN or FB_ACCESS_TOKEN == 'tu_token_de_acceso_aqui':
        errores.append("FB_ACCESS_TOKEN no configurado")
    
    try:
        from PIL import Image
    except ImportError:
        errores.append("Pillow no instalado")
    
    if errores:
        log("❌ ERRORES:", 'error')
        for e in errores:
            log(f"   • {e}", 'error')
        return False
    
    log("✅ Configuración válida", 'exito')
    
    if not verificar_tiempo():
        return False
    
    gestor = GestorRecetas()
    stats = gestor.historial.get('estadisticas', {})
    log(f"📊 Historial: {stats.get('total_publicadas', 0)} recetas")
    
    receta = seleccionar_receta(gestor)
    if not receta:
        return False
    
    log(f"📝 {receta['nombre'][:50]}...")
    texto = construir_publicacion(receta)
    hashtags = generar_hashtags(receta)
    
    log("🖼️ Imagen...")
    imagen_path = None
    
    if receta.get('imagen'):
        imagen_path = descargar_imagen_receta(receta['imagen'])
    
    if not imagen_path:
        imagen_path = crear_imagen_receta(
            receta['nombre'],
            receta.get('categoria', 'Plato'),
            traducir_area(receta.get('area', 'Internacional'))
        )
    
    if not imagen_path:
        log("❌ Sin imagen", 'error')
        return False
    
    exito = publicar_facebook(texto, imagen_path, hashtags)
    
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        gestor.guardar_receta(receta['id'], receta['nombre'], receta.get('categoria', 'General'))
        nuevo_estado = {'ultima_publicacion': datetime.now().isoformat()}
        guardar_json(ESTADO_PATH, nuevo_estado)
        log("🎉 ¡RECETA FITNESS PUBLICADA!", 'exito')
        return True
    else:
        log("❌ Falló", 'error')
        return False

if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        log("🛑 Interrumpido", 'advertencia')
        sys.exit(130)
    except Exception as e:
        log(f"💥 Error: {e}", 'error')
        import traceback
        traceback.print_exc()
        sys.exit(1)
