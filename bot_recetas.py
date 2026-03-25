#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍳 Bot de Recetas "Cocinando Rico" para Facebook - V1.0
Publica recetas deliciosas diariamente con imágenes atractivas
"""

import requests
import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont
import textwrap

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

# APIs de Recetas (TheMealDB es gratuita y no requiere key para desarrollo)
THEMEALDB_API = "https://www.themealdb.com/api/json/v1/1"
EDAMAM_APP_ID = os.getenv('EDAMAM_APP_ID')
EDAMAM_API_KEY = os.getenv('EDAMAM_API_KEY')

# Facebook
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

# Rutas
HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_recetas.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot.json')

# Tiempos y límites
TIEMPO_ENTRE_PUBLICACIONES = int(os.getenv('TIEMPO_ENTRE_PUBLICACIONES', '360'))  # 6 horas
UMBRAL_SIMILITUD = 0.75
MAX_HISTORIAL = 100

# ═══════════════════════════════════════════════════════════════
# CATEGORÍAS Y TIPOS DE COCINA
# ═══════════════════════════════════════════════════════════════

CATEGORIAS_POPULARES = [
    "Beef", "Chicken", "Dessert", "Lamb", 
    "Pasta", "Pork", "Seafood", "Vegetarian"
]

AREAS_COCINA = [
    "American", "British", "Canadian", "Chinese", 
    "French", "Indian", "Italian", "Mexican", 
    "Spanish", "Thai", "Vietnamese"
]

PALABRAS_CLAVE_DULCE = [
    "dulce", "postre", "torta", "pastel", "galleta", 
    "helado", "chocolate", "vainilla", "caramelo", "mousse"
]

PALABRAS_CLAVE_SALADO = [
    "pollo", "carne", "pescado", "pasta", "ensalada", 
    "sopa", "guiso", "parrilla", "horno", "frito"
]

# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ═══════════════════════════════════════════════════════════════

def log(mensaje, tipo='info'):
    """Sistema de logging con emojis"""
    iconos = {
        'info': 'ℹ️', 
        'exito': '✅', 
        'error': '❌', 
        'advertencia': '⚠️', 
        'cocina': '👨‍🍳',
        'debug': '🔍'
    }
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {iconos.get(tipo, 'ℹ️')} {mensaje}")

def cargar_json(ruta, default=None):
    """Carga archivo JSON con manejo de errores"""
    if default is None:
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else default.copy()
        except Exception as e:
            log(f"Error cargando JSON {ruta}: {e}", 'error')
            return default.copy()
    return default.copy()

def guardar_json(ruta, datos):
    """Guarda datos en JSON de forma segura"""
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
    """Genera hash MD5 para detectar duplicados"""
    if not texto:
        return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def calcular_similitud(s1, s2):
    """Calcula similitud entre dos strings"""
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

def traducir_categoria(categoria_en):
    """Traduce categorías al español"""
    traducciones = {
        "Beef": "Carne de Res",
        "Chicken": "Pollo",
        "Dessert": "Postres",
        "Lamb": "Cordero",
        "Miscellaneous": "Varios",
        "Pasta": "Pasta",
        "Pork": "Cerdo",
        "Seafood": "Mariscos",
        "Side": "Acompañamientos",
        "Starter": "Entradas",
        "Vegan": "Vegano",
        "Vegetarian": "Vegetariano",
        "Breakfast": "Desayuno",
        "Goat": "Cabra"
    }
    return traducciones.get(categoria_en, categoria_en)

def traducir_area(area_en):
    """Traduce áreas geográficas al español"""
    traducciones = {
        "American": "Americana",
        "British": "Británica",
        "Canadian": "Canadiense",
        "Chinese": "China",
        "Croatian": "Croata",
        "Dutch": "Holandesa",
        "Egyptian": "Egipcia",
        "Filipino": "Filipina",
        "French": "Francesa",
        "Greek": "Griega",
        "Indian": "India",
        "Irish": "Irlandesa",
        "Italian": "Italiana",
        "Jamaican": "Jamaicana",
        "Japanese": "Japonesa",
        "Kenyan": "Keniana",
        "Malaysian": "Malaya",
        "Mexican": "Mexicana",
        "Moroccan": "Marroquí",
        "Polish": "Polaca",
        "Portuguese": "Portuguesa",
        "Russian": "Rusa",
        "Spanish": "Española",
        "Thai": "Tailandesa",
        "Tunisian": "Tunecina",
        "Turkish": "Turca",
        "Ukrainian": "Ucraniana",
        "Unknown": "Internacional",
        "Vietnamese": "Vietnamita"
    }
    return traducciones.get(area_en, area_en)

# ═══════════════════════════════════════════════════════════════
# GESTIÓN DE RECETAS
# ═══════════════════════════════════════════════════════════════

class GestorRecetas:
    def __init__(self):
        self.historial = self.cargar_historial()
        
    def cargar_historial(self):
        """Carga el historial de recetas publicadas"""
        default = {
            'ids_recetas': [],
            'hashes': [],
            'timestamps': [],
            'nombres': [],
            'categorias': [],
            'estadisticas': {'total_publicadas': 0}
        }
        h = cargar_json(HISTORIAL_PATH, default)
        for k in default:
            if k not in h:
                h[k] = default[k]
        self.limpiar_historial_antiguo(h)
        return h
    
    def limpiar_historial_antiguo(self, h):
        """Elimina recetas antiguas (más de 30 días)"""
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
                    
            if len(h.get('hashes', [])) > MAX_HISTORIAL:
                for key in ['ids_recetas', 'hashes', 'timestamps', 'nombres', 'categorias']:
                    h[key] = h[key][-MAX_HISTORIAL:]
        except Exception as e:
            log(f"Error limpiando historial: {e}", 'error')
    
    def receta_ya_publicada(self, id_receta, nombre):
        """Verifica si una receta ya fue publicada"""
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
        """Guarda una receta en el historial"""
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
        
        guardar_json(HISTORIAL_PATH, self.historial)
        log(f"💾 Receta guardada en historial. Total: {self.historial['estadisticas']['total_publicadas']}", 'exito')

# ═══════════════════════════════════════════════════════════════
# OBTENCIÓN DE RECETAS (TheMealDB API)
# ═══════════════════════════════════════════════════════════════

def obtener_receta_aleatoria():
    """Obtiene una receta aleatoria de TheMealDB"""
    try:
        url = f"{THEMEALDB_API}/random.php"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if data and data.get('meals'):
            return procesar_receta_themealdb(data['meals'][0])
        return None
    except Exception as e:
        log(f"Error obteniendo receta aleatoria: {e}", 'error')
        return None

def obtener_receta_por_categoria(categoria):
    """Obtiene recetas por categoría"""
    try:
        # Primero filtrar por categoría
        url = f"{THEMEALDB_API}/filter.php?c={categoria}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if not data or not data.get('meals'):
            return None
        
        # Elegir una receta aleatoria de la lista
        import random
        receta_basica = random.choice(data['meals'])
        
        # Obtener detalles completos
        return obtener_detalles_receta(receta_basica['idMeal'])
    except Exception as e:
        log(f"Error obteniendo receta por categoría {categoria}: {e}", 'error')
        return None

def obtener_receta_por_area(area):
    """Obtiene recetas por área geográfica"""
    try:
        url = f"{THEMEALDB_API}/filter.php?a={area}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if not data or not data.get('meals'):
            return None
        
        import random
        receta_basica = random.choice(data['meals'])
        return obtener_detalles_receta(receta_basica['idMeal'])
    except Exception as e:
        log(f"Error obteniendo receta por área {area}: {e}", 'error')
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
        log(f"Error obteniendo detalles de receta {id_receta}: {e}", 'error')
        return None

def procesar_receta_themealdb(datos):
    """Procesa los datos crudos de TheMealDB"""
    receta = {
        'id': datos.get('idMeal'),
        'nombre': datos.get('strMeal'),
        'categoria': datos.get('strCategory'),
        'area': datos.get('strArea'),
        'instrucciones': datos.get('strInstructions', ''),
        'imagen': datos.get('strMealThumb'),
        'video': datos.get('strYoutube', ''),
        'fuente': datos.get('strSource', ''),
        'ingredientes': []
    }
    
    # Extraer ingredientes y medidas
    for i in range(1, 21):
        ingrediente = datos.get(f'strIngredient{i}')
        medida = datos.get(f'strMeasure{i}')
        
        if ingrediente and ingrediente.strip():
            receta['ingredientes'].append({
                'nombre': ingrediente.strip(),
                'cantidad': medida.strip() if medida else 'al gusto'
            })
    
    return receta

def buscar_receta_por_nombre(nombre):
    """Busca recetas por nombre"""
    try:
        url = f"{THEMEALDB_API}/search.php?s={nombre}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if data and data.get('meals'):
            return [procesar_receta_themealdb(m) for m in data['meals']]
        return []
    except Exception as e:
        log(f"Error buscando receta '{nombre}': {e}", 'error')
        return []

# ═══════════════════════════════════════════════════════════════
# EDAMAM API (Recetas en Español)
# ═══════════════════════════════════════════════════════════════

def obtener_receta_edamam(consulta=""):
    """Obtiene recetas de Edamam (soporta español)"""
    if not EDAMAM_APP_ID or not EDAMAM_API_KEY:
        return None
    
    try:
        url = "https://api.edamam.com/api/recipes/v2"
        params = {
            'type': 'public',
            'q': consulta or 'popular',
            'app_id': EDAMAM_APP_ID,
            'app_key': EDAMAM_API_KEY,
            'random': 'true',
            'lang': 'es'
        }
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if data and data.get('hits'):
            import random
            hit = random.choice(data['hits'])
            receta = hit.get('recipe', {})
            
            return {
                'id': receta.get('uri', '').split('_')[-1],
                'nombre': receta.get('label', 'Receta sin nombre'),
                'categoria': receta.get('dishType', ['Plato'])[0] if receta.get('dishType') else 'Plato',
                'area': receta.get('cuisineType', ['Internacional'])[0] if receta.get('cuisineType') else 'Internacional',
                'instrucciones': receta.get('url', 'Ver instrucciones en el enlace'),
                'imagen': receta.get('image'),
                'video': '',
                'fuente': receta.get('source', 'Edamam'),
                'ingredientes': [{'nombre': ing, 'cantidad': ''} for ing in receta.get('ingredientLines', [])],
                'url_original': receta.get('url'),
                'calorias': int(receta.get('calories', 0)),
                'tiempo': receta.get('totalTime', 0)
            }
        return None
    except Exception as e:
        log(f"Error obteniendo receta de Edamam: {e}", 'error')
        return None

# ═══════════════════════════════════════════════════════════════
# GENERACIÓN DE CONTENIDO
# ═══════════════════════════════════════════════════════════════

def formatear_ingredientes(ingredientes):
    """Formatea la lista de ingredientes"""
    if not ingredientes:
        return "Ingredientes no disponibles"
    
    lineas = []
    for ing in ingredientes[:12]:  # Máximo 12 ingredientes
        cantidad = ing.get('cantidad', '')
        nombre = ing.get('nombre', '')
        if cantidad and cantidad != 'al gusto':
            lineas.append(f"• {cantidad} {nombre}")
        else:
            lineas.append(f"• {nombre}")
    
    return '\n'.join(lineas)

def formatear_instrucciones(instrucciones):
    """Formatea las instrucciones en pasos numerados"""
    if not instrucciones:
        return "Instrucciones no disponibles"
    
    # Limpiar y dividir en pasos
    texto = instrucciones.replace('\r', '\n')
    pasos = [p.strip() for p in texto.split('\n') if p.strip() and len(p.strip()) > 10]
    
    if len(pasos) <= 1:
        # Si no hay saltos de línea, intentar dividir por puntos
        oraciones = [o.strip() for o in texto.split('.') if len(o.strip()) > 20]
        pasos = oraciones
    
    # Formatear máximo 5 pasos
    pasos_formateados = []
    for i, paso in enumerate(pasos[:5], 1):
        # Limitar longitud de cada paso
        if len(paso) > 200:
            paso = paso[:197] + "..."
        pasos_formateados.append(f"{i}. {paso}")
    
    return '\n\n'.join(pasos_formateados)

def construir_publicacion(receta):
    """Construye el texto de la publicación para Facebook"""
    nombre = receta['nombre']
    categoria = traducir_categoria(receta.get('categoria', 'Plato'))
    area = traducir_area(receta.get('area', 'Internacional'))
    
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
        "💡 Tip: ¡Comparte esta receta con quienes aman cocinar!",
        "",
        f"🔗 Fuente: {receta.get('fuente', 'TheMealDB')}"
    ]
    
    # Añadir enlace si existe
    if receta.get('url_original'):
        lineas.append(f"📖 Receta completa: {receta['url_original']}")
    
    return '\n'.join(lineas)

def generar_hashtags(receta):
    """Genera hashtags relevantes"""
    nombre = receta.get('nombre', '').lower()
    categoria = receta.get('categoria', '').lower()
    area = receta.get('area', '').lower()
    
    hashtags = ['#CocinandoRico', '#Recetas', '#Cocina']
    
    # Hashtags por categoría
    if any(p in categoria for p in ['dessert', 'postre', 'dulce']):
        hashtags.extend(['#Postres', '#Dulces', '#Reposteria'])
    elif any(p in categoria for p in ['chicken', 'pollo']):
        hashtags.extend(['#Pollo', '#RecetasConPollo'])
    elif any(p in categoria for p in ['beef', 'carne', 'res']):
        hashtags.extend(['#Carne', '#Res', '#Parrilla'])
    elif any(p in categoria for p in ['seafood', 'marisco', 'pescado']):
        hashtags.extend(['#Mariscos', '#Pescado', '#Saludable'])
    else:
        hashtags.extend(['#ComidaCasera', '#RecetaDelDia'])
    
    # Hashtags por área
    area_tags = {
        'italian': '#CocinaItaliana',
        'mexican': '#CocinaMexicana',
        'spanish': '#CocinaEspanola',
        'chinese': '#CocinaChina',
        'french': '#CocinaFrancesa',
        'indian': '#CocinaHindu',
        'american': '#CocinaAmericana'
    }
    
    for key, tag in area_tags.items():
        if key in area:
            hashtags.append(tag)
            break
    
    return ' '.join(hashtags)

# ═══════════════════════════════════════════════════════════════
# GENERACIÓN DE IMÁGENES
# ═══════════════════════════════════════════════════════════════

def descargar_imagen_receta(url_imagen):
    """Descarga y valida la imagen de la receta"""
    if not url_imagen:
        return None
    
    try:
        from io import BytesIO
        
        response = requests.get(url_imagen, timeout=20, stream=True)
        if response.status_code != 200:
            return None
        
        img = Image.open(BytesIO(response.content))
        
        # Validar tamaño mínimo
        w, h = img.size
        if w < 400 or h < 300:
            log(f"Imagen muy pequeña: {w}x{h}", 'advertencia')
            return None
        
        # Convertir a RGB si es necesario
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Redimensionar manteniendo proporción
        img.thumbnail((1200, 1200))
        
        # Guardar temporalmente
        hash_img = generar_hash(url_imagen)[:10]
        path = f'/tmp/receta_{hash_img}.jpg'
        img.save(path, 'JPEG', quality=90)
        
        if os.path.getsize(path) < 10000:
            os.remove(path)
            return None
            
        return path
        
    except Exception as e:
        log(f"Error descargando imagen: {e}", 'error')
        return None

def crear_imagen_receta(nombre_receta, categoria, area):
    """Crea una imagen personalizada si no hay imagen disponible"""
    try:
        # Colores según categoría
        colores = {
            'Dessert': ('#8B4513', '#FFD700'),      # Marrón/Dorado
            'Seafood': ('#1E3A5F', '#87CEEB'),      # Azul marino/Celeste
            'Vegetarian': ('#228B22', '#90EE90'),   # Verde bosque/Verde claro
            'Chicken': ('#DAA520', '#FFE4B5'),      # Dorado/Beige
            'Beef': ('#8B0000', '#FFA07A'),         # Rojo oscuro/Salmón
        }
        
        bg_color, accent_color = colores.get(categoria, ('#FF6B35', '#FFE66D'))
        
        # Crear imagen
        img = Image.new('RGB', (1200, 630), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Intentar cargar fuentes
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font_title = font_sub = font_small = ImageFont.load_default()
        
        # Barra decorativa superior
        draw.rectangle([(0, 0), (1200, 12)], fill=accent_color)
        
        # Título centrado
        titulo = textwrap.fill(nombre_receta[:60], width=30)
        y_pos = 200
        
        draw.text((600, y_pos), titulo, font=font_title, fill='white', anchor="mm")
        
        # Categoría y área
        info = f"{traducir_area(area)} • {traducir_categoria(categoria)}"
        draw.text((600, 400), info, font=font_sub, fill=accent_color, anchor="mm")
        
        # Footer
        draw.text((600, 550), "🍳 Cocinando Rico", font=font_small, fill='white', anchor="mm")
        draw.text((600, 580), "Recetas deliciosas para cada día", font=font_small, fill='#CCCCCC', anchor="mm")
        
        # Guardar
        hash_nombre = generar_hash(nombre_receta)[:10]
        path = f'/tmp/receta_gen_{hash_nombre}.jpg'
        img.save(path, 'JPEG', quality=95)
        
        return path
        
    except Exception as e:
        log(f"Error creando imagen: {e}", 'error')
        return None

# ═══════════════════════════════════════════════════════════════
# PUBLICACIÓN EN FACEBOOK
# ═══════════════════════════════════════════════════════════════

def publicar_facebook(texto, imagen_path, hashtags):
    """Publica en Facebook con imagen"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales de Facebook", 'error')
        return False
    
    mensaje = f"{texto}\n\n{hashtags}\n\n— 🍳 Cocinando Rico | Recetas deliciosas para cada día"
    
    # Truncar si es muy largo
    if len(mensaje) > 2200:
        lineas = texto.split('\n')
        texto_cortado = ""
        for linea in lineas:
            if len(texto_cortado + linea + "\n") < 1800:
                texto_cortado += linea + "\n"
            else:
                break
        mensaje = f"{texto_cortado.rstrip()}\n\n[Ver receta completa en el enlace]\n\n{hashtags}\n\n— 🍳 Cocinando Rico"
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            files = {'file': ('receta.jpg', f, 'image/jpeg')}
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN
            }
            
            response = requests.post(url, files=files, data=data, timeout=60)
            result = response.json()
            
            if 'id' in result:
                log(f"✅ Publicado en Facebook. ID: {result['id']}", 'exito')
                return True
            else:
                error_msg = result.get('error', {}).get('message', 'Error desconocido')
                log(f"❌ Error Facebook: {error_msg}", 'error')
                return False
                
    except Exception as e:
        log(f"❌ Excepción publicando: {e}", 'error')
        return False

# ═══════════════════════════════════════════════════════════════
# FLUJO PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def verificar_tiempo():
    """Verifica si ha pasado el tiempo mínimo entre publicaciones"""
    estado = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    ultima = estado.get('ultima_publicacion')
    
    if not ultima:
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        minutos_transcurridos = (datetime.now() - ultima_dt).total_seconds() / 60
        
        if minutos_transcurridos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última publicación hace {minutos_transcurridos:.0f} minutos", 'info')
            return False
    except:
        pass
    
    return True

def seleccionar_receta(gestor):
    """Selecciona una receta nueva válida"""
    receta = None
    intentos = 0
    max_intentos = 30
    
    # Estrategias de búsqueda
    estrategias = [
        lambda: obtener_receta_aleatoria(),
        lambda: obtener_receta_por_categoria('Dessert'),
        lambda: obtener_receta_por_categoria('Chicken'),
        lambda: obtener_receta_por_categoria('Pasta'),
        lambda: obtener_receta_por_area('Italian'),
        lambda: obtener_receta_por_area('Mexican'),
        lambda: obtener_receta_por_area('Spanish'),
    ]
    
    # Intentar con Edamam si está configurado
    if EDAMAM_APP_ID and EDAMAM_API_KEY:
        estrategias.insert(0, lambda: obtener_receta_edamam())
    
    while intentos < max_intentos and not receta:
        for estrategia in estrategias:
            if intentos >= max_intentos:
                break
                
            intentos += 1
            try:
                candidata = estrategia()
                
                if not candidata:
                    continue
                
                id_receta = candidata.get('id')
                nombre = candidata.get('nombre')
                
                if not id_receta or not nombre:
                    continue
                
                log(f"Probando: {nombre[:50]}...", 'debug')
                
                # Verificar duplicados
                es_dup, razon = gestor.receta_ya_publicada(id_receta, nombre)
                if es_dup:
                    log(f"   ❌ Duplicado ({razon}): {nombre[:40]}...", 'debug')
                    continue
                
                # Validar que tenga ingredientes e instrucciones
                if len(candidata.get('ingredientes', [])) < 3:
                    log(f"   ⚠️ Pocos ingredientes", 'debug')
                    continue
                
                log(f"   ✅ Receta seleccionada: {nombre}", 'exito')
                return candidata
                
            except Exception as e:
                log(f"Error en estrategia: {e}", 'error')
                continue
    
    return None

def main():
    """Función principal del bot"""
    print("\n" + "="*60)
    print("🍳 COCINANDO RICO BOT - V1.0")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Verificar credenciales
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales de Facebook (FB_PAGE_ID, FB_ACCESS_TOKEN)", 'error')
        return False
    
    # Verificar tiempo entre publicaciones
    if not verificar_tiempo():
        return False
    
    # Inicializar gestor
    gestor = GestorRecetas()
    log(f"📊 Historial cargado: {gestor.historial['estadisticas']['total_publicadas']} recetas publicadas")
    
    # Seleccionar receta
    log("🔍 Buscando receta deliciosa...", 'cocina')
    receta = seleccionar_receta(gestor)
    
    if not receta:
        log("ERROR: No se pudo encontrar una receta válida", 'error')
        return False
    
    # Construir publicación
    log(f"📝 Preparando: {receta['nombre']}")
    texto_publicacion = construir_publicacion(receta)
    hashtags = generar_hashtags(receta)
    
    # Procesar imagen
    log("🖼️ Procesando imagen...")
    imagen_path = None
    
    # Intentar descargar imagen original
    if receta.get('imagen'):
        imagen_path = descargar_imagen_receta(receta['imagen'])
    
    # Crear imagen personalizada si falla
    if not imagen_path:
        log("🎨 Creando imagen personalizada...", 'advertencia')
        imagen_path = crear_imagen_receta(
            receta['nombre'],
            receta.get('categoria', 'Plato'),
            receta.get('area', 'Internacional')
        )
    
    if not imagen_path:
        log("ERROR: No se pudo obtener imagen", 'error')
        return False
    
    # Publicar
    log("📤 Publicando en Facebook...")
    exito = publicar_facebook(texto_publicacion, imagen_path, hashtags)
    
    # Limpiar archivo temporal
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
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
        log("✅ ¡Receta publicada exitosamente!", 'exito')
        return True
    else:
        log("❌ Falló la publicación", 'error')
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
