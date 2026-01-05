import requests
import praw
import gspread
import os
import json
import random
import base64  # IMPORTANTE PARA LA DECODIFICACIÓN
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
GSPREAD_CREDENTIALS_FILE = "credentials.json"
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
        # Obtenemos todos los nombres de la columna B (índice 1)
        rows = worksheet.get("B2:B50")
        return set([row[0] for row in rows if row])
    except Exception as e:
        print(f"⚠️ No se pudo leer historial de la hoja: {e}")
        return set()

def get_random_product(used_names):
    print("🔍 Buscando producto en Sovrn (Auto-Mode)...")
    
    # Context Rotation
    random_page_url = random.choice(CONTEXT_URLS)
    print(f"🧠 Contexto: {random_page_url}")
    
    query = {"apiKey": SOVRN_API_KEY, "pageUrl": random_page_url}
    payload = {"market": "usd_en", "num_products": 50, "exclude_merchants": [], "force_cpr_scoring": False}
    
    try:
        r = requests.post(SOVRN_URL, params=query, json=payload, headers=SOVRN_HEADERS, timeout=10)
        if r.status_code == 200:
            all_products = r.json()
            random.shuffle(all_products)
            
            # Filtramos: Precio > $20 Y Nombre NO usado
            candidates = [
                p for p in all_products 
                if float(p.get('salePrice', 0)) > 20 and p['name'] not in used_names
            ]
            
            print(f"✨ Candidatos válidos: {len(candidates)}")
            
            if len(candidates) > 0:
                return candidates[0]
            else:
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
        print("✅ Google Sheet actualizado.")
    except Exception as e:
        print(f"❌ Error Google Sheet: {e}")

def post_to_reddit_image(product, image_path):
    print("🔌 Conectando a Reddit...")
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            password=REDDIT_PASSWORD,
            user_agent=f"script:DailyDoseBot:v1.0 (by /u/{REDDIT_USERNAME})",
            username=REDDIT_USERNAME
        )
        
        subreddit = reddit.subreddit("dailydosecoolfinds")
        
        clean_title = f"{product['name']} - Just ${product['salePrice']} 🔥"
        caption = f"""
**Found this amazing deal!** 📦

Check out full review and best price on my website below.

**[👉 CLICK HERE TO VIEW PRODUCT & DEAL](https://dailydosecoolfinds.com)**
"""

        submission = subreddit.submit_image(
            title=clean_title,
            image_path=image_path,
            flair_id=FLAIR_ID
        )
        
        reddit_permalink = f"https://www.reddit.com{submission.permalink}"
        print("✅ POST CREADO.")
        print(f"🔗 Link: {reddit_permalink}")
        
        update_google_sheet(product, clean_title, reddit_permalink, worksheet)
        return True
    except Exception as e:
        print(f"❌ Error Reddit: {e}")
        return False

# ==========================================
# EJECUCIÓN AUTOMÁTICA (BASE64 MODE)
# ==========================================
if __name__ == "__main__":
    print(f"🚀 Bot iniciando a las {datetime.now().strftime('%H:%M:%S')}")
    
    # Variables Globales
    sh = None
    worksheet = None
    
    # 1. RECUPERAR CREDENCIALES DE GITHUB SECRETS (MODO BASE64)
    b64_str = os.getenv('GOOGLE_CREDS_B64')
    
    if not b64_str:
        print("❌ ERROR: No se encontró el secreto GOOGLE_CREDS_B64.")
        exit()
    
    try:
        print("✅ Decodificando Base64 (Modo Seguro)...")
        
        # Decodificar Base64 directamente a Bytes
        creds_bytes = base64.b64decode(b64_str)
        
        # Escribir los Bytes directos al archivo
        with open('temp_creds.json', 'wb') as f:
            f.write(creds_bytes)
            
        # Conectar usando el archivo generado
        gc = gspread.service_account(filename='temp_creds.json')
        sh = gc.open_by_key(SHEET_KEY)
        worksheet = sh.worksheet(SHEET_NAME)
        print("✅ Conexión Google Sheets exitosa (Base64).")
        
    except Exception as e:
        print(f"❌ Fatal: {e}")
        exit()

    # 2. Cargar Historial
    used_names = get_history_from_sheet(worksheet)
    print(f"📂 Productos ya posteados: {len(used_names)}")

    # 3. Buscar Producto
    prod = get_random_product(used_names)
    if not prod:
        print("⚠️ No se encontraron productos nuevos.")
        exit()

    print(f"🎯 Producto: {prod['name']}")

    # 4. Descargar Imagen
    img_file = download_image(prod['imageURL'])
    if not img_file:
        exit()

    # 5. Publicar en Reddit (Automático)
    success = post_to_reddit_image(prod, img_file)
    
    # 6. Limpieza
    if success:
        if os.path.exists(img_file):
            os.remove(img_file)
        if os.path.exists('temp_creds.json'):
            os.remove('temp_creds.json')
    
    print("🏁 Ejecución finalizada.")
