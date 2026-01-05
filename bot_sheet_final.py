import requests
import praw
import gspread
import os
import json
import random
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN SOVRN
# ==========================================
SOVRN_API_KEY = "134070ee62245f1bfe18f4f36288aa7a"
SOVRN_SECRET = "3077f2bbbca0cf7e5a929176bc6e017b5c10339c"
SOVRN_URL = "https://shopping-gallery.prd-commerce.sovrnservices.com/ai-orchestration/products"
SOVRN_HEADERS = {
    "Authorization": f"secret {SOVRN_SECRET}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# ==========================================
# 2. CONFIGURACIÓN GOOGLE SHEETS
# ==========================================
GSPREAD_CREDENTIALS_FILE = "credentials.json" # Solo para local, en Actions se usa env
SHEET_KEY = "1AfB-Sdn9ZgZXqfHLDFiZSmIap9WeXnwVzrNT-zKctlM"
SHEET_NAME = "DailyDoseCoolFinds_Content"

# ==========================================
# 3. CONFIGURACIÓN REDDIT
# ==========================================
REDDIT_CLIENT_ID = "vBYT7GqUOhaqCTFivCHw6A"
REDDIT_CLIENT_SECRET = "Z0QhUNoC8WZtR3klaXOcUi9IvRFOyA"
REDDIT_USERNAME = "amzcoolfinds"
REDDIT_PASSWORD = "Mamita01@*"
FLAIR_ID = "463a2860-dd0e-11f0-a489-92c8b64e1845" 

# ==========================================
# 4. CONFIGURACIÓN DE CONTENIDO & HISTORIAL
# ==========================================
# En GitHub Actions usamos la Hoja de Google como Historial para persistencia
CONTEXT_URLS = [
    "https://www.youtube.com/@EvateExplica",
    "https://www.wired.com/gear/",
    "https://www.amazon.com/gp/goldbox",
    "https://www.wayfair.com/keyword.php?keyword=decor",
    "https://www.target.com/c/electronics/-/N-5xtt0"
]

# ==========================================
# 5. FUNCIONES
# ==========================================

def get_history_from_sheet(worksheet):
    """Lee la columna B de la hoja para saber qué productos ya hemos posteado"""
    try:
        # Asumimos que el historial empieza en la fila 2
        # Obtenemos todos los nombres de la columna B (índice 1 porque A es 0)
        # Limitamos a las últimas 50 filas para ahorrar tiempo
        rows = worksheet.get("B2:B50")
        # rows devuelve una lista de listas [['Nombre1'], ['Nombre2']]
        return set([row[0] for row in rows if row])
    except Exception as e:
        print(f"⚠️ No se pudo leer historial de la hoja: {e}")
        return set()

def get_random_product(used_names):
    print("🔍 Buscando producto en Sovrn (Auto-Mode)...")
    
    # Context Rotation
    random_page_url = random.choice(CONTEXT_URLS)
    print(f"🧠 AI Contexto actual: {random_page_url}")
    
    query = {"apiKey": SOVRN_API_KEY, "pageUrl": random_page_url}
    
    # AUMENTADO A 50 y SIN FILTRO DE TIENDAS PARA TENER VARIEDAD
    payload = {
        "market": "usd_en", 
        "num_products": 50, 
        "exclude_merchants": [], 
        "force_cpr_scoring": False
    }
    
    try:
        r = requests.post(SOVRN_URL, params=query, json=payload, headers=SOVRN_HEADERS, timeout=10)
        if r.status_code == 200:
            all_products = r.json()
            print(f"📦 Sovrn devolvió {len(all_products)} productos candidatos.")
            
            # 1. BARAJAR (SHUFFLE): Desordena la lista para romper patrones repetitivos
            random.shuffle(all_products)
            
            # 2. Filtramos: Precio > $20 Y ID no usado
            candidates = [
                p for p in all_products 
                if float(p.get('salePrice', 0)) > 20 and p['name'] not in used_names
            ]
            
            print(f"✨ Después de filtrar repetidos y baratos, quedan {len(candidates)} opciones.")
            
            if len(candidates) > 0:
                selected = candidates[0]
                print(f"🎯 Producto ELEGIDO: {selected['name']}")
                return selected
            else:
                print("⚠️ Todos los candidatos encontrados ya han sido usados o son baratos.")
                return None
        return None
    except Exception as e:
        print(f"❌ Error obteniendo productos: {e}")
        return None

def download_image(url, filename="temp_product.jpg"):
    print(f"📥 Descargando imagen...")
    try:
        img_data = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).content
        with open(filename, 'wb') as handler:
            handler.write(img_data)
        print("✅ Imagen descargada.")
        return filename
    except Exception as e:
        print(f"❌ Error descargando imagen: {e}")
        return None

def update_google_sheet(product, reddit_title, reddit_permalink, worksheet):
    print("📝 Guardando en Google Sheets...")
    try:
        gc = gspread.service_account(filename=GSPREAD_CREDENTIALS_FILE)
        sh = gc.open_by_key(SHEET_KEY)
        worksheet = sh.worksheet(SHEET_NAME)
        
        reddit_body = f"[Check Price](https://dailydosecoolfinds.com)"
        
        row = [
            "Tech Finds",             
            product['name'],         
            product['imageURL'],     
            reddit_title,            
            reddit_body,             
            product['deepLink'],     
            reddit_permalink         
        ]
        worksheet.append_row(row)
        print("✅ Google Sheet actualizado con todos los datos.")
    except Exception as e:
        print(f"❌ Error en Google Sheet: {e}")

def post_to_reddit_image(product, image_path):
    print("🔌 Conectando a Reddit...")
    
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        password=REDDIT_PASSWORD,
        user_agent=f"script:DailyDoseBot:v1.0 (by /u/{REDDIT_USERNAME})",
        username=REDDIT_USERNAME
    )
    
    subreddit = reddit.subreddit("dailydosecoolfinds")
    
    # 1. TÍTULO LIMPIO (Sin marca, solo producto en inglés)
    # Ejemplo: "Ergonomic Task Chair - Just $142.99" (Sin [Wayfair])
    clean_title = f"{product['name']} - Just ${product['salePrice']} 🔥"
    
    # 2. CAPTACIÓN (Hook) hacia tu Landing Page
    # Reddit no permite títulos clickeables, pero sí Markdown en el texto
    caption = f"""
**Found this amazing deal!** 📦

Check out full review and best price on my website below.

**[👉 CLICK HERE TO VIEW PRODUCT & DEAL](https://dailydosecoolfinds.com)**
"""

    try:
        submission = subreddit.submit_image(
            title=clean_title,
            image_path=image_path,
            flair_id=FLAIR_ID
        )
        
        # 3. Generamos el Permalink para guardar en la hoja (Col G)
        reddit_permalink = f"https://www.reddit.com{submission.permalink}"
        
        print("✅ POST CREADO.")
        print(f"🔗 Link: {reddit_permalink}")
        
        # 4. Pasamos los datos para guardar en la hoja
        update_google_sheet(product, clean_title, reddit_permalink)
        
        return True
    except Exception as e:
        print(f"❌ Error en Reddit: {e}")
        return False

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    print(f"🚀 Bot iniciando a las {datetime.now().strftime('%H:%M:%S')}")
    
    # 1. Cargar Historial
    used_ids = load_history()
    
    # 2. Buscar Producto Único
    prod = get_random_product(used_ids)
    if not prod:
        print("No se encontraron productos nuevos.")
        exit()

    print(f"✅ Producto: {prod['name']}")

    # 3. Descargar Imagen
    img_file = download_image(prod['imageURL'])
    if not img_file:
        exit()

    # 4. Publicar
    confirm = input("¿Publicar en Reddit y actualizar Sheet? (s/n): ")
    if confirm.lower() == 's':
        success = post_to_reddit_image(prod, img_file)
        
        if success:
            # 5. Guardar ID en historial para NO repetir
            used_ids.add(prod['id'])
            save_history(used_ids)
            os.remove(img_file)
        else:
            print("Post fallido, no se guardó en historial.")
    else:
        print("Cancelado.")
