import requests
import praw
import gspread
import os
import json
import random
import base64
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
# Solo claves de la nube
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
# 4. CONFIGURACIÓN DE CONTENIDO
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
    try:
        rows = worksheet.get("B2:B50")
        return set([row[0] for row in rows if row])
    except Exception as e:
        print(f"⚠️ No se pudo leer historial: {e}")
        return set()

def get_random_product(used_names):
    print("🔍 Buscando producto en Sovrn...")
    
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
    print("📥 Descargando imagen...")
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
            user_agent=f"script:CloudBot:v1.0 (by /u/{REDDIT_USERNAME})",
            username=REDDIT_USERNAME
        )
        
        subreddit = reddit.subreddit("dailydosecoolfinds")
        
        clean_title = f"{product['name']} - Just ${product['salePrice']} 🔥"
        caption = f"[{clean_title}](https://dailydosecoolfinds.com)"

        submission = subreddit.submit_image(
            title=clean_title,
            image_path=image_path,
            flair_id=FLAIR_ID
        )
        
        permalink = f"https://www.reddit.com{submission.permalink}"
        print("✅ POST CREADO.")
        print(f"🔗 Link: {permalink}")
        
        update_google_sheet(product, clean_title, permalink, worksheet)
        return True
    except Exception as e:
        print(f"❌ Error Reddit: {e}")
        return False

# ==========================================
# EJECUCIÓN (MODO CLOUD ONLY)
# ==========================================
if __name__ == "__main__":
    print(f"🚀 Bot iniciando a las {datetime.now().strftime('%H:%M:%S')}")
    
    # 1. RECUPERAR SECRETO BASE64 (OBLIGATORIO EN GITHUB ACTIONS)
    b64_str = os.getenv('CREDENCIALES')
    
    # VALIDACIÓN: Si no está el secreto, salimos inmediatamente
    if not b64_str:
        print("❌ ERROR CRÍTICO:")
        print("❌ La variable 'CREDENCIALES' no está configurada.")
        print("💡 SOLUCIÓN:")
        print("💡 1. Ve a tu repositorio en GitHub.")
        print("💡 2. Ve a Settings > Secrets and variables > Actions.")
        print("💡 3. Crea un secreto nuevo con este nombre exacto: CREDENCIALES")
        print("💡 4. Pega el código gigante que generaste con 'make_secret.py'.")
        exit()
    
    # 2. DECODIFICAR Y CONECTAR
    try:
        print("✅ Decodificando credenciales (Base64)...")
        # Decodificar Base64 directamente a Bytes
        creds_bytes = base64.b64decode(b64_str)
        
        # Escribir Bytes directo al archivo temporal
        with open('temp_creds.json', 'wb') as f:
            f.write(creds_bytes)
            
        # Conectar usando el archivo temporal
        gc = gspread.service_account(filename='temp_creds.json')
        sh = gc.open_by_key(SHEET_KEY)
        worksheet = sh.worksheet(SHEET_NAME)
        print("✅ Conexión Google Sheets exitosa (Nube).")
        
    except Exception as e:
        print(f"❌ Fatal: No se pudo conectar a Google Sheet: {e}")
        print(f"💡 Revisa que el secreto 'CREDENCIALES' esté pegado COMPLETO.")
        exit()

    # 3. Cargar Historial
    used_names = get_history_from_sheet(worksheet)
    print(f"📂 Productos ya posteados: {len(used_names)}")

    # 4. Buscar Producto
    prod = get_random_product(used_names)
    if not prod:
        print("⚠️ No se encontraron productos nuevos.")
        exit()

    print(f"🎯 Producto: {prod['name']}")

    # 5. Descargar Imagen
    img_file = download_image(prod['imageURL'])
    if not img_file:
        exit()

    # 6. Publicar (Automático)
    success = post_to_reddit_image(prod, img_file)
    
    # 7. Limpieza
    if success:
        if os.path.exists(img_file):
            os.remove(img_file)
        if os.path.exists('temp_creds.json'):
            os.remove('temp_creds.json')
    
    print("🏁 Ejecución finalizada.")
