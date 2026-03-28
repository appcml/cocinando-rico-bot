#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🥗 Bot de Recetas en ESPAÑOL para Facebook
Busca recetas en español, sin links externos, contenido propio
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

# APIs - Usamos Edamam para español (gratis hasta 10k llamadas/mes)
EDAMAM_APP_ID = os.getenv('EDAMAM_APP_ID')
EDAMAM_API_KEY = os.getenv('EDAMAM_API_KEY')

# Backup: TheMealDB (inglés, traducimos)
THEMEALDB_API = "https://www.themealdb.com/api/json/v1/1"

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
TIEMPO_ENTRE_PUBLICACIONES = int(os.getenv('TIEMPO_ENTRE_PUBLICACIONES', '360'))
UMBRAL_SIMILITUD = 0.75
MAX_HISTORIAL = 100

# ═══════════════════════════════════════════════════════════════
# BANCO DE RECETAS EN ESPAÑOL (Contenido Propio)
# ═══════════════════════════════════════════════════════════════

RECETAS_ESPANOL = [
    {
        'id': 'es_001',
        'nombre': 'Pechuga de Pollo a la Plancha con Vegetales',
        'categoria': 'Proteica',
        'area': 'Española',
        'tiempo': '25 minutos',
        'dificultad': 'Fácil',
        'calorias': 350,
        'proteinas': 45,
        'ingredientes': [
            {'nombre': 'Pechuga de pollo', 'cantidad': '200g'},
            {'nombre': 'Brócoli', 'cantidad': '100g'},
            {'nombre': 'Zanahoria', 'cantidad': '1 unidad'},
            {'nombre': 'Aceite de oliva', 'cantidad': '1 cucharada'},
            {'nombre': 'Ajo', 'cantidad': '2 dientes'},
            {'nombre': 'Limón', 'cantidad': '1/2 unidad'},
            {'nombre': 'Sal y pimienta', 'cantidad': 'al gusto'},
            {'nombre': 'Pimentón dulce', 'cantidad': '1 cucharadita'}
        ],
        'instrucciones': [
            'Lava y corta el brócoli en floretes pequeños. Pela y corta la zanahoria en rodajas finas.',
            'Calienta una sartén antiadherente con aceite de oliva a fuego medio-alto.',
            'Sazona la pechuga de pollo con sal, pimienta y pimentón. Colócala en la sartén.',
            'Cocina el pollo 6-7 minutos por cada lado hasta que esté dorado y cocido internamente.',
            'En la misma sartén, saltea los vegetales con ajo picado durante 5 minutos.',
            'Exprime el limón sobre el pollo y los vegetales antes de servir.',
            'Sirve caliente acompañado de una porción de arroz integral si deseas.'
        ],
        'tags': ['pollo', 'proteina', 'fitness', 'bajo en grasa']
    },
    {
        'id': 'es_002',
        'nombre': 'Filete de Salmón al Horno con Espárragos',
        'categoria': 'Proteica',
        'area': 'Mediterránea',
        'tiempo': '20 minutos',
        'dificultad': 'Fácil',
        'calorias': 420,
        'proteinas': 38,
        'ingredientes': [
            {'nombre': 'Filete de salmón', 'cantidad': '180g'},
            {'nombre': 'Espárragos verdes', 'cantidad': '150g'},
            {'nombre': 'Aceite de oliva', 'cantidad': '2 cucharadas'},
            {'nombre': 'Ajo', 'cantidad': '3 dientes'},
            {'nombre': 'Limón', 'cantidad': '1 unidad'},
            {'nombre': 'Eneldo fresco', 'cantidad': '1 cucharada'},
            {'nombre': 'Sal', 'cantidad': 'al gusto'},
            {'nombre': 'Pimienta negra', 'cantidad': 'al gusto'}
        ],
        'instrucciones': [
            'Precalienta el horno a 200°C (400°F).',
            'Lava los espárragos y corta los extremos duros. Colócalos en una bandeja.',
            'Coloca el filete de salmón sobre los espárragos en la bandeja.',
            'Mezcla el aceite, ajo picado, jugo de limón, eneldo, sal y pimienta.',
            'Vierte la mezcla sobre el salmón y los espárragos.',
            'Hornea durante 12-15 minutos hasta que el salmón se desmenuce fácilmente.',
            'Sirve inmediatamente con rodajas de limón fresco.'
        ],
        'tags': ['pescado', 'omega3', 'saludable', 'rapido']
    },
    {
        'id': 'es_003',
        'nombre': 'Ensalada de Quinoa con Pollo y Aguacate',
        'categoria': 'Fitness',
        'area': 'Latina',
        'tiempo': '30 minutos',
        'dificultad': 'Media',
        'calorias': 480,
        'proteinas': 35,
        'ingredientes': [
            {'nombre': 'Quinoa', 'cantidad': '100g cruda'},
            {'nombre': 'Pechuga de pollo', 'cantidad': '150g'},
            {'nombre': 'Aguacate', 'cantidad': '1/2 unidad'},
            {'nombre': 'Tomate cherry', 'cantidad': '150g'},
            {'nombre': 'Pepino', 'cantidad': '1/2 unidad'},
            {'nombre': 'Cilantro fresco', 'cantidad': 'al gusto'},
            {'nombre': 'Jugo de lima', 'cantidad': '2 cucharadas'},
            {'nombre': 'Aceite de oliva', 'cantidad': '1 cucharada'},
            {'nombre': 'Sal', 'cantidad': 'al gusto'}
        ],
        'instrucciones': [
            'Enjuaga la quinoa y cocínala según las instrucciones del paquete (generalmente 15 min). Deja enfriar.',
            'Sazona la pechuga con sal y pimienta. Cocínala a la plancha 7 minutos por lado. Corta en cubos.',
            'Corta el aguacate, tomates y pepino en cubos medianos.',
            'En un tazón grande, mezcla la quinoa fría con el pollo y los vegetales.',
            'Agrega cilantro picado, jugo de lima y aceite de oliva. Mezcla suavemente.',
            'Sirve fría o a temperatura ambiente. Ideal para meal prep.'
        ],
        'tags': ['quinoa', 'superalimento', 'mealprep', 'completa']
    },
    {
        'id': 'es_004',
        'nombre': 'Tacos de Carne Asada con Cebolla y Cilantro',
        'categoria': 'Proteica',
        'area': 'Mexicana',
        'tiempo': '25 minutos',
        'dificultad': 'Media',
        'calorias': 520,
        'proteinas': 42,
        'ingredientes': [
            {'nombre': 'Carne de res para asar', 'cantidad': '300g'},
            {'nombre': 'Tortillas de maíz', 'cantidad': '4 unidades'},
            {'nombre': 'Cebolla blanca', 'cantidad': '1 unidad'},
            {'nombre': 'Cilantro fresco', 'cantidad': '1 manojo'},
            {'nombre': 'Limón', 'cantidad': '2 unidades'},
            {'nombre': 'Ajo', 'cantidad': '4 dientes'},
            {'nombre': 'Comino molido', 'cantidad': '1 cucharadita'},
            {'nombre': 'Chile en polvo', 'cantidad': '1/2 cucharadita'},
            {'nombre': 'Sal', 'cantidad': 'al gusto'},
            {'nombre': 'Aceite vegetal', 'cantidad': '2 cucharadas'}
        ],
        'instrucciones': [
            'Corta la carne en tiras delgadas contra la fibra. Sazona con ajo, comino, chile y sal.',
            'Marina la carne con jugo de limón durante 15 minutos.',
            'Calienta el aceite en un sartén o comal a fuego alto.',
            'Cocina la carne 3-4 minutos moviendo constantemente hasta que esté dorada.',
            'Calienta las tortillas directamente en el comal hasta que estén suaves.',
            'Sirve la carne en las tortillas con cebolla picada y cilantro fresco.',
            'Acompaña con rodajas de limón y salsa al gusto.'
        ],
        'tags': ['tacos', 'carne', 'mexicana', 'asado']
    },
    {
        'id': 'es_005',
        'nombre': 'Omelette de Claras con Espinacas y Champiñones',
        'categoria': 'Baja en Grasa',
        'area': 'Francesa',
        'tiempo': '15 minutos',
        'dificultad': 'Fácil',
        'calorias': 220,
        'proteinas': 28,
        'ingredientes': [
            {'nombre': 'Claras de huevo', 'cantidad': '4 unidades (120ml)'},
            {'nombre': 'Yema de huevo', 'cantidad': '1 unidad'},
            {'nombre': 'Espinacas frescas', 'cantidad': '1 taza'},
            {'nombre': 'Champiñones', 'cantidad': '100g'},
            {'nombre': 'Cebolla', 'cantidad': '1/4 unidad'},
            {'nombre': 'Aceite en spray', 'cantidad': 'c/n'},
            {'nombre': 'Sal', 'cantidad': 'al gusto'},
            {'nombre': 'Pimienta', 'cantidad': 'al gusto'},
            {'nombre': 'Pimentón', 'cantidad': 'pizca'}
        ],
        'instrucciones': [
            'Lava y corta los champiñones en láminas. Pica la cebolla finamente.',
            'Bate las claras con la yema, sal y pimienta hasta integrar (no espumar).',
            'Saltea cebolla y champiñones en sartén antiadherente 3 minutos.',
            'Agrega las espinacas y cocina hasta que se marchiten (1 minuto). Retira.',
            'Rocía el sartén con aceite en spray. Vierte los huevos batidos.',
            'Cocina a fuego medio. Cuando los bordes cuajen, agrega el relleno en un lado.',
            'Dobla el omelette con cuidado. Cocina 1 minuto más y sirve caliente.'
        ],
        'tags': ['desayuno', 'claras', 'bajo en grasa', 'definicion']
    },
    {
        'id': 'es_006',
        'nombre': 'Lomo de Cerdo a la Mostaza con Batatas',
        'categoria': 'Proteica',
        'area': 'Española',
        'tiempo': '40 minutos',
        'dificultad': 'Media',
        'calorias': 580,
        'proteinas': 48,
        'ingredientes': [
            {'nombre': 'Lomo de cerdo', 'cantidad': '250g'},
            {'nombre': 'Batatas', 'cantidad': '200g'},
            {'nombre': 'Mostaza dijón', 'cantidad': '2 cucharadas'},
            {'nombre': 'Miel', 'cantidad': '1 cucharada'},
            {'nombre': 'Romero fresco', 'cantidad': '2 ramas'},
            {'nombre': 'Ajo', 'cantidad': '3 dientes'},
            {'nombre': 'Aceite de oliva', 'cantidad': '2 cucharadas'},
            {'nombre': 'Sal', 'cantidad': 'al gusto'},
            {'nombre': 'Pimienta', 'cantidad': 'al gusto'}
        ],
        'instrucciones': [
            'Precalienta el horno a 180°C (350°F).',
            'Pela y corta las batatas en cubos medianos. Mezcla con 1 cucharada de aceite, sal y pimienta.',
            'Coloca las batatas en bandeja y hornea 20 minutos.',
            'Mezcla mostaza, miel, ajo picado y romero picado.',
            'Sella el lomo de cerdo en sartén con aceite 2 minutos por lado.',
            'Unta la mezcla de mostaza sobre el cerdo. Colócalo sobre las batatas parcialmente cocidas.',
            'Hornea todo junto 15-20 minutos más hasta que el cerdo alcance 63°C interno.',
            'Deja reposar 5 minutos antes de cortar. Sirve con las batatas doradas.'
        ],
        'tags': ['cerdo', 'batata', 'horno', 'sustanciosa']
    },
    {
        'id': 'es_007',
        'nombre': 'Atún a la Plancha con Salsa de Sésamo y Jengibre',
        'categoria': 'Proteica',
        'area': 'Asiática',
        'tiempo': '15 minutos',
        'dificultad': 'Media',
        'calorias': 380,
        'proteinas': 45,
        'ingredientes': [
            {'nombre': 'Filetes de atún fresco', 'cantidad': '200g'},
            {'nombre': 'Salsa de soja baja en sodio', 'cantidad': '2 cucharadas'},
            {'nombre': 'Jengibre fresco', 'cantidad': '1 cucharada rallada'},
            {'nombre': 'Ajo', 'cantidad': '2 dientes'},
            {'nombre': 'Aceite de sésamo', 'cantidad': '1 cucharadita'},
            {'nombre': 'Semillas de sésamo', 'cantidad': '1 cucharada'},
            {'nombre': 'Cebollín', 'cantidad': '2 tallos'},
            {'nombre': 'Limón', 'cantidad': '1/2 unidad'},
            {'nombre': 'Pimienta', 'cantidad': 'al gusto'}
        ],
        'instrucciones': [
            'Mezcla salsa de soja, jengibre rallado, ajo picado y aceite de sésamo. Reserva.',
            'Sazona los filetes de atún con pimienta. No agregues sal aún (la salsa es salada).',
            'Calienta sartén o parrilla a fuego alto hasta que esté muy caliente.',
            'Sella el atún 1-2 minutos por lado (debe quedar rosado en el centro).',
            'Retira del fuego y baña inmediatamente con la mezcla de sésamo caliente.',
            'Espolvorea semillas de sésamo tostadas y cebollín picado.',
            'Sirve con rodajas de limón. Acompaña de arroz integral o ensalada de algas.'
        ],
        'tags': ['atun', 'asiatica', 'rapida', 'omega3']
    },
    {
        'id': 'es_008',
        'nombre': 'Bowl de Pavo Molido con Garbanzos y Verduras',
        'categoria': 'Fitness',
        'area': 'Mediterránea',
        'tiempo': '30 minutos',
        'dificultad': 'Fácil',
        'calorias': 450,
        'proteinas': 40,
        'ingredientes': [
            {'nombre': 'Pavo molido magro', 'cantidad': '200g'},
            {'nombre': 'Garbanzos cocidos', 'cantidad': '150g'},
            {'nombre': 'Pimiento rojo', 'cantidad': '1 unidad'},
            {'nombre': 'Calabacín', 'cantidad': '1 unidad'},
            {'nombre': 'Cebolla', 'cantidad': '1/2 unidad'},
            {'nombre': 'Ajo', 'cantidad': '3 dientes'},
            {'nombre': 'Comino', 'cantidad': '1 cucharadita'},
            {'nombre': 'Pimentón', 'cantidad': '1 cucharadita'},
            {'nombre': 'Aceite de oliva', 'cantidad': '1 cucharada'},
            {'nombre': 'Sal', 'cantidad': 'al gusto'},
            {'nombre': 'Cilantro', 'cantidad': 'al gusto'}
        ],
        'instrucciones': [
            'Corta el pimiento, calabacín y cebolla en cubos pequeños del mismo tamaño.',
            'Calienta aceite en sartén grande a fuego medio-alto.',
            'Agrega cebolla y ajo, cocina 2 minutos hasta que estén transparentes.',
            'Añade el pavo molido. Desmenúzalo con espátula y cocina 5 minutos.',
            'Incorpora los garbanzos, pimiento y calabacín. Mezcla bien.',
            'Añade comino, pimentón y sal. Cocina 8-10 minutos moviendo ocasionalmente.',
            'Rectifica sazón y sirve en bowls calientes con cilantro fresco.',
            'Opcional: agrega una cucharada de yogur griego como topping.'
        ],
        'tags': ['pavo', 'garbanzos', 'bowl', 'sustanciosa']
    },
    {
        'id': 'es_009',
        'nombre': 'Merluza al Horno con Almendras y Limón',
        'categoria': 'Ligera',
        'area': 'Española',
        'tiempo': '20 minutos',
        'dificultad': 'Fácil',
        'calorias': 280,
        'proteinas': 35,
        'ingredientes': [
            {'nombre': 'Filetes de merluza', 'cantidad': '250g'},
            {'nombre': 'Almendras fileteadas', 'cantidad': '30g'},
            {'nombre': 'Limón', 'cantidad': '1 unidad'},
            {'nombre': 'Ajo', 'cantidad': '2 dientes'},
            {'nombre': 'Perejil fresco', 'cantidad': '2 cucharadas'},
            {'nombre': 'Vino blanco', 'cantidad': '2 cucharadas'},
            {'nombre': 'Aceite de oliva', 'cantidad': '2 cucharadas'},
            {'nombre': 'Sal', 'cantidad': 'al gusto'},
            {'nombre': 'Pimienta', 'cantidad': 'al gusto'}
        ],
        'instrucciones': [
            'Precalienta el horno a 200°C (400°F).',
            'Coloca los filetes de merluza en bandeja engrasada. Sazona con sal y pimienta.',
            'Exprime jugo de medio limón sobre el pescado. Vierte el vino blanco en la bandeja.',
            'Mezcla el aceite con ajo picado y perejil. Distribuye sobre los filetes.',
            'Espolvorea las almendras fileteadas encima del pescado.',
            'Hornea 12-15 minutos hasta que el pescado esté opaco y se desmenuce fácilmente.',
            'Sirve inmediatamente con rodajas de limón fresco y más perejil.'
        ],
        'tags': ['pescado', 'ligero', 'almendras', 'rapida']
    },
    {
        'id': 'es_010',
        'nombre': 'Wrap de Pollo Buffalo con Lechuga y Tomate',
        'categoria': 'Fitness',
        'area': 'Americana',
        'tiempo': '20 minutos',
        'dificultad': 'Fácil',
        'calorias': 420,
        'proteinas': 38,
        'ingredientes': [
            {'nombre': 'Pechuga de pollo cocida', 'cantidad': '150g'},
            {'nombre': 'Tortillas integrales grandes', 'cantidad': '1 unidad'},
            {'nombre': 'Salsa buffalo baja en grasa', 'cantidad': '2 cucharadas'},
            {'nombre': 'Lechuga romana', 'cantidad': '2 hojas grandes'},
            {'nombre': 'Tomate', 'cantidad': '1/2 unidad'},
            {'nombre': 'Zanahoria rallada', 'cantidad': '1/4 taza'},
            {'nombre': 'Yogur griego natural', 'cantidad': '2 cucharadas'},
            {'nombre': 'Cebollín', 'cantidad': '1 tallo'},
            {'nombre': 'Pimienta', 'cantidad': 'al gusto'}
        ],
        'instrucciones': [
            'Corta la pechuga de pollo en tiras o cubos. Mezcla con la salsa buffalo caliente.',
            'Lava y seca las hojas de lechuga. Corta el tomate en rodajas finas.',
            'Calienta la tortilla integral 20 segundos en microondas para hacerla flexible.',
            'Unta el centro de la tortilla con yogur griego (esto equilibra el picante).',
            'Coloca la lechuga como base. Agrega el pollo buffalo encima.',
            'Añade tomate, zanahoria y cebollín picado.',
            'Cierra el wrap doblando los lados y enrollando firmemente.',
            'Corta por la mitad y sirve inmediatamente, o envuelve en papel aluminio para llevar.'
        ],
        'tags': ['wrap', 'pollo', 'buffalo', 'para llevar']
    }
]

# Más recetas se pueden agregar aquí...

# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ═══════════════════════════════════════════════════════════════

def log(mensaje, tipo='info'):
    iconos = {
        'info': 'ℹ️', 'exito': '✅', 'error': '❌', 'advertencia': '⚠️', 
        'cocina': '👨‍🍳', 'debug': '🔍', 'facebook': '📘', 'proteina': '💪'
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
# SELECCIÓN DE RECETAS EN ESPAÑOL
# ═══════════════════════════════════════════════════════════════

def obtener_receta_espanola():
    """Obtiene receta del banco de recetas en español"""
    global RECETAS_ESPANOL
    
    # Mezclar para variación
    recetas_disponibles = RECETAS_ESPANOL.copy()
    random.shuffle(recetas_disponibles)
    
    for receta in recetas_disponibles:
        return receta  # Retorna la primera (aleatoria por el shuffle)
    
    return None

# ═══════════════════════════════════════════════════════════════
# GENERACIÓN DE CONTENIDO (SIN LINKS EXTERNOS)
# ═══════════════════════════════════════════════════════════════

def formatear_ingredientes(ingredientes):
    if not ingredientes:
        return "• Ingredientes no disponibles"
    
    lineas = []
    for ing in ingredientes:
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
        'merluza': '🐟', 'huevo': '🥚', 'claras': '🥚', 'yema': '🥚',
        'proteina': '💪', 'pechuga': '🍗', 'filete': '🥩',
        'arroz': '🍚', 'quinoa': '🌾', 'pasta': '🍝', 'papa': '🥔',
        'batata': '🍠', 'tomate': '🍅', 'cebolla': '🧅', 'ajo': '🧄',
        'aceite': '🛢️', 'sal': '🧂', 'pimienta': '🌶️', 'limón': '🍋',
        'queso': '🧀', 'leche': '🥛', 'yogur': '🥣', 'crema': '🥛',
        'harina': '🌾', 'azúcar': '🍬', 'agua': '💧', 'vino': '🍷',
        'espinaca': '🥬', 'brócoli': '🥦', 'zanahoria': '🥕', 'pepino': '🥒',
        'pimiento': '🫑', 'calabacín': '🥒', 'aguacate': '🥑',
        'almendra': '🥜', 'garbanzo': '🥔', 'espárrago': '🥬',
        'cilantro': '🌿', 'perejil': '🌿', 'romero': '🌿', 'eneldo': '🌿',
        'jengibre': '🫚', 'mostaza': '🟡', 'salsa': '🥫', 'miel': '🍯',
        'tortilla': '🌮', 'wrap': '🌯', 'taco': '🌮', 'bowl': '🥣',
        'parrilla': '🔥', 'asado': '🔥', 'horno': '♨️', 'plancha': '🍳',
        'default': '•'
    }
    
    for key, emoji in emojis.items():
        if key in ingrediente_lower:
            return emoji
    return emojis['default']

def formatear_instrucciones(instrucciones):
    if not instrucciones:
        return "Instrucciones no disponibles."
    
    if isinstance(instrucciones, list):
        pasos = instrucciones
    else:
        pasos = [instrucciones]
    
    pasos_formateados = []
    for i, paso in enumerate(pasos[:6], 1):  # Máximo 6 pasos
        if len(paso) > 220:
            paso = paso[:217] + "..."
        pasos_formateados.append(f"{i}. {paso}")
    
    return '\n\n'.join(pasos_formateados)

def construir_publicacion(receta):
    nombre = receta['nombre']
    categoria = receta.get('categoria', 'Fitness')
    area = receta.get('area', 'Internacional')
    tiempo = receta.get('tiempo', '30 minutos')
    dificultad = receta.get('dificultad', 'Media')
    calorias = receta.get('calorias', 400)
    proteinas = receta.get('proteinas', 30)
    
    lineas = [
        f"💪 {nombre}",
        "",
        f"📍 {area} • {categoria}",
        f"⏱️ {tiempo} • 🎯 {dificultad}",
        f"🔥 {calorias} kcal • 🥩 {proteinas}g proteína",
        "",
        "📝 INGREDIENTES:",
        formatear_ingredientes(receta.get('ingredientes', [])),
        "",
        "👨‍🍳 PREPARACIÓN:",
        formatear_instrucciones(receta.get('instrucciones', [])),
        "",
        "─────────────────",
        "💡 CONSEJO FITNESS:",
        "• Consume esta receta dentro de la hora posterior a tu entrenamiento para máxima absorción de proteínas.",
        "• Acompaña con 1 vaso grande de agua para mejor digestión.",
        "• Puedes preparar porciones dobles y guardar en táper para el día siguiente.",
        "",
        "🔥 ¿La preparaste? Cuéntanos cómo te quedó en los comentarios 👇",
        "",
        "💪 COCINA FITNESS PRO",
        "Recetas diseñadas para ganar músculo y perder grasa"
    ]
    
    return '\n'.join(lineas)

def generar_hashtags(receta):
    categoria = receta.get('categoria', '').lower()
    tags = receta.get('tags', [])
    area = receta.get('area', '').lower()
    
    hashtags = [
        '#ComidaFitness', '#RecetasProteicas', '#CocinaSaludable',
        '#FitnessEspañol', '#NutricionDeportiva', '#GymLife'
    ]
    
    # Hashtags por categoría
    if 'proteica' in categoria:
        hashtags.extend(['#AltaEnProteina', '#GanarMusculo', '#BodyBuilding'])
    elif 'fitness' in categoria:
        hashtags.extend(['#ComidaFit', '#HealthyFood', '#DietaEquilibrada'])
    elif 'baja' in categoria:
        hashtags.extend(['#BajoEnGrasa', '#Definicion', '#PerderGrasa'])
    elif 'ligera' in categoria:
        hashtags.extend(['#Ligero', '#Saludable', '#Detox'])
    
    # Hashtags por área
    areas = {
        'española': '#CocinaEspañolaFit',
        'mexicana': '#ComidaMexicanaFit',
        'mediterranea': '#DietaMediterranea',
        'latina': '#CocinaLatinaFit',
        'asiática': '#ComidaAsiaticaFit',
        'americana': '#FitnessUSA',
        'francesa': '#CocinaFrancesaFit'
    }
    
    for key, tag in areas.items():
        if key in area:
            hashtags.append(tag)
            break
    
    # Hashtags por tags específicos
    tag_map = {
        'pollo': '#PolloFitness', 'carne': '#CarneProteica',
        'pescado': '#PescadoFit', 'atun': '#AtunProteico',
        'desayuno': '#DesayunoFitness', 'postre': '#PostreSaludable',
        'rapida': '#RecetaRapida', 'mealprep': '#MealPrep',
        'bowl': '#BowlProteico', 'wrap': '#WrapFitness',
        'tacos': '#TacosFit', 'parrilla': '#ParrillaFit',
        'horno': '#AlHorno', 'bajo en grasa': '#LowFat'
    }
    
    for tag in tags:
        tag_lower = tag.lower()
        for key, hashtag in tag_map.items():
            if key in tag_lower:
                hashtags.append(hashtag)
                break
    
    return ' '.join(hashtags[:10])  # Máximo 10 hashtags

# ═══════════════════════════════════════════════════════════════
# IMÁGENES FITNESS
# ═══════════════════════════════════════════════════════════════

def crear_imagen_receta(nombre_receta, categoria, proteinas):
    """Crea imagen atractiva estilo fitness"""
    try:
        # Colores según tipo de receta
        if 'proteica' in categoria.lower():
            bg_color = '#1a1a2e'  # Azul oscuro profesional
            accent_color = '#e94560'  # Rojo energía
            text_color = '#eaeaea'
        elif 'baja' in categoria.lower():
            bg_color = '#2d5016'  # Verde salud
            accent_color = '#76c893'
            text_color = '#ffffff'
        else:
            bg_color = '#0f3460'  # Azul fitness
            accent_color = '#e94560'
            text_color = '#eaeaea'
        
        img = Image.new('RGB', (1200, 630), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except:
            font_title = font_sub = font_small = font_badge = ImageFont.load_default()
        
        # Barra superior energía
        draw.rectangle([(0, 0), (1200, 15)], fill=accent_color)
        
        # Badge de proteínas (destacado)
        badge_width = 280
        badge_height = 80
        badge_x = 900
        badge_y = 50
        draw.rounded_rectangle(
            [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
            radius=15,
            fill=accent_color
        )
        draw.text((badge_x + badge_width//2, badge_y + badge_height//2), 
                 f"💪 {proteinas}g PROTEÍNA", 
                 font=font_badge, fill='white', anchor="mm")
        
        # Título principal
        titulo = textwrap.fill(nombre_receta[:70], width=28)
        draw.text((80, 200), titulo, font=font_title, fill=text_color)
        
        # Info secundaria
        draw.text((80, 380), "🔥 ALTA EN PROTEÍNAS • BAJO EN GRASA", 
                 font=font_sub, fill=accent_color)
        
        # Footer profesional
        draw.rectangle([(0, 580), (1200, 630)], fill='#16213e')
        draw.text((600, 605), "💪 COCINA FITNESS PRO • Recetas para Resultados Reales", 
                 font=font_small, fill='#a0a0a0', anchor="mm")
        
        # Guardar
        hash_nombre = generar_hash(nombre_receta)[:10]
        path = os.path.join('/tmp', f'receta_fit_{hash_nombre}.jpg')
        img.save(path, 'JPEG', quality=95, optimize=True)
        
        return path
        
    except Exception as e:
        log(f"Error creando imagen: {e}", 'error')
        return None

# ═══════════════════════════════════════════════════════════════
# FACEBOOK (SIN LINKS EXTERNOS)
# ═══════════════════════════════════════════════════════════════

def publicar_facebook(texto, imagen_path):
    """Publica en Facebook sin links externos"""
    if not FB_PAGE_ID or FB_PAGE_ID == 'tu_page_id_aqui':
        log("❌ FB_PAGE_ID no configurado", 'error')
        return False
    
    if not FB_ACCESS_TOKEN or FB_ACCESS_TOKEN == 'tu_token_de_acceso_aqui':
        log("❌ FB_ACCESS_TOKEN no configurado", 'error')
        return False
    
    log(f"📘 Publicando...", 'facebook')
    
    # Mensaje completo sin links externos
    mensaje = texto  # Ya incluye todo el contenido y hashtags
    
    # Verificar límite de caracteres (2200 para Facebook)
    if len(mensaje) > 2200:
        log(f"✂️ Truncando mensaje ({len(mensaje)} chars)", 'advertencia')
        # Cortar manteniendo la estructura
        partes = mensaje.split('─────────────────')
        if len(partes) > 1:
            mensaje = partes[0][:1800] + "\n\n[Ver receta completa en comentarios]\n\n" + partes[1]
    
    if not os.path.exists(imagen_path):
        log(f"❌ Imagen no existe", 'error')
        return False
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            files = {'file': ('receta.jpg', f, 'image/jpeg')}
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN,
                'published': 'true'
            }
            
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
    """Selecciona receta en español no publicada"""
    max_intentos = len(RECETAS_ESPANOL) * 2
    
    log(f"🔍 Buscando receta en ESPAÑOL...", 'cocina')
    
    for intento in range(max_intentos):
        receta = obtener_receta_espanola()
        
        if not receta:
            continue
        
        id_receta = receta.get('id')
        nombre = receta.get('nombre')
        
        if not id_receta or not nombre:
            continue
        
        es_dup, razon = gestor.receta_ya_publicada(id_receta, nombre)
        if es_dup:
            log(f"   ↳ Ya publicada: {nombre[:40]}...", 'debug')
            continue
        
        log(f"   ✅ NUEVA RECETA: {nombre}", 'exito')
        return receta
    
    log("❌ Todas las recetas ya fueron publicadas", 'error')
    log("   💡 Considera agregar más recetas al banco de datos", 'advertencia')
    return None

def main():
    print("\n" + "="*70)
    print("💪 COCINA FITNESS PRO - ESPAÑOL")
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
    log(f"📊 Historial: {stats.get('total_publicadas', 0)} recetas publicadas")
    log(f"📚 Banco de recetas: {len(RECETAS_ESPANOL)} disponibles")
    
    receta = seleccionar_receta(gestor)
    if not receta:
        return False
    
    log(f"📝 Preparando: {receta['nombre'][:50]}...")
    texto = construir_publicacion(receta)
    hashtags = generar_hashtags(receta)
    
    # Combinar texto y hashtags
    publicacion_completa = f"{texto}\n\n{hashtags}"
    
    log("🖼️ Creando imagen fitness...")
    imagen_path = crear_imagen_receta(
        receta['nombre'],
        receta.get('categoria', 'Fitness'),
        receta.get('proteinas', 30)
    )
    
    if not imagen_path:
        log("❌ Sin imagen", 'error')
        return False
    
    exito = publicar_facebook(publicacion_completa, imagen_path)
    
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        gestor.guardar_receta(receta['id'], receta['nombre'], receta.get('categoria', 'Fitness'))
        nuevo_estado = {'ultima_publicacion': datetime.now().isoformat()}
        guardar_json(ESTADO_PATH, nuevo_estado)
        log("🎉 ¡RECETA FITNESS PUBLICADA EN ESPAÑOL!", 'exito')
        return True
    else:
        log("❌ Falló publicación", 'error')
        return False

if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        log("🛑 Interrumpido", 'advertencia')
        sys.exit(130)
    except Exception as e:
        log(f"💥 Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        sys.exit(1)
