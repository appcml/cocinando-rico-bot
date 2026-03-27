#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍳 Bot de Recetas "Cocinando Rico" para Facebook - V1.2 (ESTADO ROBUSTO)
Maneja estado_bot.json vacío o corrupto
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
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas")
except ImportError:
    print("⚠️ python-dotenv no instalado")

# APIs
THEMEALDB_API = "https://www.themealdb.com/api/json/v1/1"

# Facebook
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

# Edamam (opcional)
EDAMAM_APP_ID = os.getenv('EDAMAM_APP_ID')
EDAMAM_API_KEY = os.getenv('EDAMAM_API_KEY')

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', os.path.join(DATA_DIR, 'historial_recetas.json'))
ESTADO_PATH = os.getenv('ESTADO_PATH', os.path.join(DATA_DIR, 'estado_bot.json'))

# Tiempos
TIEMPO_ENTRE_PUBLICACIONES = int(os.getenv('TIEMPO_ENTRE_PUBLICACIONES', '1'))
UMBRAL_SIMILITUD = 0.75
MAX_HISTORIAL = 100

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

def log(mensaje, tipo='info'):
    iconos = {
        'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 
        'cocina': '👨‍🍳', 'debug': '🔍', 'facebook': '📘', 'api': '🌐'
    }
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {iconos.get(tipo, 'ℹ️')} {mensaje}", flush=True)

# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE ARCHIVOS - CORREGIDAS PARA MANEJAR ARCHIVOS VACÍOS
# ═══════════════════════════════════════════════════════════════

def cargar_json_seguro(ruta, default=None):
    """
    Carga JSON de forma segura, manejando:
    - Archivo no existe
    - Archivo vacío
    - Archivo con solo espacios
    - JSON corrupto
    """
    if default is None:
        default = {}
    
    # Si no existe, crear con default
    if not os.path.exists(ruta):
        log(f"📁 Creando archivo nuevo: {os.path.basename(ruta)}", 'info')
        guardar_json(ruta, default)
        return default.copy()
    
    # Verificar si es directorio
    if os.path.isdir(ruta):
        log(f"❌ Error: {ruta} es un directorio", 'error')
        return default.copy()
    
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # VERIFICAR SI ESTÁ VACÍO O SOLO TIENE ESPACIOS
        if not content or not content.strip():
            log(f"📄 Archivo vacío: {os.path.basename(ruta)}", 'advertencia')
            log(f"   ↳ Inicializando...", 'info')
            guardar_json(ruta, default)
            return default.copy()
        
        # Intentar parsear JSON
        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError as e:
            log(f"❌ JSON corrupto: {e}", 'error')
            
            # Backup del archivo corrupto
            try:
                backup = f"{ruta}.corrupto.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                os.rename(ruta, backup)
                log(f"💾 Backup: {backup}", 'advertencia')
            except:
                pass
            
            # Crear nuevo archivo limpio
            guardar_json(ruta, default)
            return default.copy()
            
    except PermissionError:
        log(f"❌ Sin permisos: {ruta}", 'error')
        return default.copy()
    except Exception as e:
        log(f"❌ Error leyendo {ruta}: {e}", 'error')
        return default.copy()

def guardar_json(ruta, datos):
    """Guarda JSON de forma segura"""
    try:
        directorio = os.path.dirname(ruta)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        
        temp_path = f"{ruta}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        os.replace(temp_path, ruta)
        return True
        
    except Exception as e:
        log(f"❌ Error guardando {ruta}: {e}", 'error')
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
                    
        except Exception as e:
            log(f"⚠️ Error limpiando: {e}", 'advertencia')
    
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
        
        if guardar_json(HISTORIAL_PATH, self.historial):
            log(f"💾 Total: {stats['total_publicadas']} recetas", 'exito')

# ═══════════════════════════════════════════════════════════════
# OBTENCIÓN DE RECETAS
# ═══════════════════════════════════════════════════════════════

def obtener_receta_aleatoria():
    try:
        log("🌐 TheMealDB...", 'api')
        url = f"{THEMEALDB_API}/random.php"
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            log(f"   ❌ HTTP {response.status_code}", 'error')
            return None
        
        data = response.json()
        
        if not data or not data.get('meals'):
            log("   ❌ Sin recetas", 'error')
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
        
        import random
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
        'nombre': datos.get('strMeal', 'Sin nombre'),
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
    for ing in ingredientes[:10]:
        cantidad = ing.get('cantidad', '')
        nombre = ing.get('nombre', '')
        
        if cantidad and cantidad.lower() != 'al gusto':
            lineas.append(f"• {cantidad} {nombre}")
        else:
            lineas.append(f"• {nombre}")
    
    return '\n'.join(lineas)

def formatear_instrucciones(instrucciones):
    if not instrucciones:
        return "Instrucciones no disponibles."
    
    texto = instrucciones.replace('\r', '\n').strip()
    pasos = [l.strip() for l in texto.split('\n') if l.strip() and len(l.strip()) > 20]
    
    if len(pasos) < 2:
        oraciones = [o.strip() for o in texto.split('.') if len(o.strip()) > 30]
        pasos = oraciones
    
    pasos_formateados = []
    for i, paso in enumerate(pasos[:4], 1):
        if len(paso) > 180:
            paso = paso[:177] + "..."
        pasos_formateados.append(f"{i}. {paso}")
    
    return '\n\n'.join(pasos_formateados)

def construir_publicacion(receta):
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
        "💡 ¿La preparaste? Cuéntanos en los comentarios 👇",
    ]
    
    if receta.get('fuente') and receta['fuente'] != 'TheMealDB':
        lineas.append(f"")
        lineas.append(f"🔗 {receta['fuente']}")
    
    return '\n'.join(lineas)

def generar_hashtags(receta):
    categoria = receta.get('categoria', '').lower()
    area = receta.get('area', '').lower()
    
    hashtags = ['#CocinandoRico', '#Recetas', '#CocinaCasera']
    
    if 'dessert' in categoria or 'postre' in categoria:
        hashtags.extend(['#Postres', '#Reposteria'])
    elif 'chicken' in categoria:
        hashtags.extend(['#Pollo'])
    elif 'beef' in categoria or 'carne' in categoria:
        hashtags.extend(['#Carne'])
    elif 'pasta' in categoria:
        hashtags.extend(['#Pasta'])
    elif 'seafood' in categoria:
        hashtags.extend(['#Mariscos'])
    elif 'vegetarian' in categoria or 'vegan' in categoria:
        hashtags.extend(['#Vegetariano'])
    
    areas_map = {
        'italian': '#CocinaItaliana',
        'mexican': '#CocinaMexicana',
        'spanish': '#CocinaEspañola',
        'chinese': '#CocinaChina',
        'french': '#CocinaFrancesa',
        'indian': '#CocinaHindu',
        'american': '#CocinaAmericana'
    }
    
    for key, tag in areas_map.items():
        if key in area:
            hashtags.append(tag)
            break
    
    return ' '.join(hashtags)

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
        paletas = {
            'Dessert': ('#8B4513', '#FFD700', '#FFF8DC'),
            'Seafood': ('#1E3A5F', '#87CEEB', '#E0F6FF'),
            'Vegetarian': ('#228B22', '#90EE90', '#F0FFF0'),
            'Vegan': ('#2E8B57', '#98FB98', '#F5FFFA'),
            'Chicken': ('#DAA520', '#FFE4B5', '#FFFAF0'),
            'Beef': ('#8B0000', '#FFA07A', '#FFE4E1'),
            'Pasta': ('#FF6347', '#FFD700', '#FFFACD'),
        }
        
        bg_color, accent_color, text_bg = paletas.get(categoria, ('#FF6B35', '#FFE66D', '#FFF5EE'))
        
        img = Image.new('RGB', (1200, 630), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font_title = font_sub = font_small = ImageFont.load_default()
        
        draw.rectangle([(0, 0), (1200, 15)], fill=accent_color)
        draw.rectangle([(50, 150), (1150, 480)], fill=text_bg)
        
        titulo = textwrap.fill(nombre_receta[:80], width=28)
        draw.text((100, 200), titulo, font=font_title, fill='#333333')
        
        info = f"🍳 {area} • {categoria}"
        draw.text((100, 400), info, font=font_sub, fill=bg_color)
        
        draw.rectangle([(0, 580), (1200, 630)], fill='#2C3E50')
        draw.text((600, 605), "Cocinando Rico 🥘 Recetas deliciosas", 
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
    
    mensaje = f"{texto}\n\n{hashtags}\n\n— 🍳 Cocinando Rico | Recetas deliciosas"
    
    if len(mensaje) > 2200:
        lineas = texto.split('\n')
        texto_cortado = ""
        for linea in lineas:
            if len(texto_cortado + linea + "\n") < 1800:
                texto_cortado += linea + "\n"
            else:
                break
        mensaje = f"{texto_cortado.rstrip()}\n\n[Continúa en comentarios]\n\n{hashtags}\n\n— 🍳 Cocinando Rico"
    
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
# FLUJO PRINCIPAL - USANDO cargar_json_seguro
# ═══════════════════════════════════════════════════════════════

def verificar_tiempo():
    """CORREGIDO: Usa cargar_json_seguro para manejar archivo vacío"""
    # ANTES (fallaba con archivo vacío):
    # estado = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    
    # AHORA (maneja archivo vacío/corrupto):
    estado = cargar_json_seguro(ESTADO_PATH, {'ultima_publicacion': None})
    
    ultima = estado.get('ultima_publicacion')
    
    # Si no hay última publicación, permitir ejecutar
    if not ultima:
        log("📝 Primera ejecución (sin historial previo)", 'info')
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
            
    except Exception as e:
        log(f"⚠️ Error en fecha '{ultima}': {e}", 'advertencia')
        return True  # Permitir por precaución

def seleccionar_receta(gestor):
    categorias = ['Dessert', 'Chicken', 'Pasta', 'Seafood', 'Vegetarian', 'Beef']
    max_intentos = 20
    
    log(f"🔍 Buscando receta...", 'cocina')
    
    for intento in range(max_intentos):
        receta = obtener_receta_aleatoria()
        
        if not receta and intento > 5:
            cat = categorias[intento % len(categorias)]
            receta = obtener_receta_por_categoria(cat)
        
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
        
        log(f"   ✅ {nombre}", 'exito')
        return receta
    
    log("❌ No se encontró receta", 'error')
    return None

def main():
    print("\n" + "="*70)
    print("🍳 COCINANDO RICO BOT - V1.2")
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
    
    # Verificar tiempo (AHORA MANEJA ESTADO VACÍO)
    if not verificar_tiempo():
        return False
    
    # Inicializar
    gestor = GestorRecetas()
    stats = gestor.historial.get('estadisticas', {})
    log(f"📊 Historial: {stats.get('total_publicadas', 0)} recetas")
    
    # Seleccionar receta
    receta = seleccionar_receta(gestor)
    if not receta:
        return False
    
    # Preparar contenido
    log(f"📝 {receta['nombre'][:50]}...")
    texto = construir_publicacion(receta)
    hashtags = generar_hashtags(receta)
    
    # Procesar imagen
    log("🖼️ Imagen...")
    imagen_path = None
    
    if receta.get('imagen'):
        imagen_path = descargar_imagen_receta(receta['imagen'])
    
    if not imagen_path:
        imagen_path = crear_imagen_receta(
            receta['nombre'],
            receta.get('categoria', 'Plato'),
            receta.get('area', 'Internacional')
        )
    
    if not imagen_path:
        log("❌ Sin imagen", 'error')
        return False
    
    # Publicar
    exito = publicar_facebook(texto, imagen_path, hashtags)
    
    # Limpieza
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    # Guardar estado
    if exito:
        gestor.guardar_receta(receta['id'], receta['nombre'], receta.get('categoria', 'General'))
        
        # GUARDAR ESTADO CON TIMESTAMP
        nuevo_estado = {'ultima_publicacion': datetime.now().isoformat()}
        if guardar_json(ESTADO_PATH, nuevo_estado):
            log("💾 Estado guardado", 'exito')
        
        log("🎉 ¡RECETA PUBLICADA!", 'exito')
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
