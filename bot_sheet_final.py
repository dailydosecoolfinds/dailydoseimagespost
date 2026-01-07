import requests
import praw
import gspread
import os
import json
import random
import base64
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN (SECRETS Y APIS)
# ==========================================
# IMPORTANTE: Vuelve a poner tus claves reales aquí si las borraste en el paso anterior.

SOVRN_API_KEY = "134070ee62245f1bfe18f4f36288aa7a"
SOVRN_SECRET = "TU_SOVRN_SECRET_AQUI"
SOVRN_URL = "https://shopping-gallery.prd-commerce.sovrnservices.com/ai-orchestration/products"
SOVRN_HEADERS = {
    "Authorization": f"secret {SOVRN_SECRET}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

SHEET_KEY = "1AfB-Sdn9ZgZXqfHLDFiZSmIap9WeXnwVzrNT-zKctlM"
SHEET_NAME = "DailyDoseCoolFinds_Content"

REDDIT_CLIENT_ID = "vBYT7GqUOhaqCTFivCHw6A"
REDDIT_CLIENT_SECRET = "Z0QhUNoC8WZtR3klaXOcUi9IvRFOyA"
REDDIT_USERNAME = "amzcoolfinds"
REDDIT_PASSWORD = "TU_REDDIT_PASSWORD_AQUI"
FLAIR_ID = "463a2860-dd0e-11f0-a489-92c8b64e1845"

CONTEXT_URLS = [
    "https://www.youtube.com/@EvateExplica",
    "https://www.wired.com/gear/",
    "https://www.amazon.com/gp/goldbox",
    "https://www.wayfair.com/keyword.php?keyword=decor",
    "https://www.target.com/c/electronics/-/N-5xtt0"
]

# ==========================================
# 2. FUNCIONES
# ==========================================

def get_history_from_sheet(worksheet):
    print("📂 Leyendo historial de Google Sheets...")
    try:
        rows = worksheet.get("B2:B1000")
        return set([row[0] for row in rows if row])
    except Exception as e:
        print(f"⚠️ No se pudo leer historial: {e}")
        return set()

def get_random_product(used_names):
    print("🔍 Buscando producto nuevo en Sovrn...")
    random_page_url = random.choice(CONTEXT_URLS)
    query = {"apiKey": SOVRN_API_KEY, "pageUrl": random_page_url}
    payload = {"market": "usd_en", "num_products": 50, "exclude_merchants": [], "force_cpr_scoring": False}
    
    try:
        r = requests.post(SOVRN_URL, params=query, json=payload, headers=SOVRN_HEADERS, timeout=15)
        if r.status_code == 200:
            all_products = r.json()
            random.shuffle(all_products)
            candidates = [
                p for p in all_products 
                if float(p.get('salePrice', 0)) > 20 and p['name'] not in used_names
            ]
            print(f"✨ Candidatos encontrados: {len(candidates)}")
            if candidates:
                return candidates[0]
    except Exception as e:
        print(f"❌ Error API Sovrn: {e}")
    return None

def download_image(url, filename="temp_product.jpg"):
    print("📥 Descargando imagen...")
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            with open(filename, 'wb') as handler:
                handler.write(r.content)
            print("✅ Imagen lista.")
            return filename
    except Exception as e:
        print(f"❌ Error imagen: {e}")
    return None

def update_google_sheet(product, reddit_title, reddit_permalink, worksheet):
    print("📝 Actualizando Google Sheet...")
    try:
        reddit_body = f"[Check Price](https://dailydosecoolfinds.com)"
        row = [
            "Tech Finds", product['name'], product['imageURL'], reddit_title, reddit_body, product['deepLink'], reddit_permalink
        ]
        worksheet.append_row(row)
        print("✅ Fila agregada exitosamente.")
    except Exception as e:
        print(f"❌ Error escribiendo en Sheet: {e}")

def post_to_reddit_image(product, image_path, worksheet):
    print("🔌 Publicando en Reddit...")
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
        submission = subreddit.submit_image(title=clean_title, image_path=image_path, flair_id=FLAIR_ID)
        permalink = f"https://www.reddit.com{submission.permalink}"
        print(f"✅ POST CREADO: {permalink}")
        update_google_sheet(product, clean_title, permalink, worksheet)
        return True
    except Exception as e:
        print(f"❌ Error Reddit: {e}")
        return False

# ==========================================
# 3. EJECUCIÓN PRINCIPAL (CLOUD ONLY)
# ==========================================
if __name__ == "__main__":
    print(f"🚀 Bot iniciando (Modo GitHub Actions) - {datetime.now()}")

    b64_creds = os.getenv('CREDENCIALES')
    if not b64_creds:
        print("❌ ERROR FATAL: No se encontró el secreto 'CREDENCIALES'.")
        exit(1)

    try:
        print("🔓 Decodificando credenciales...")
        decoded_str = base64.b64decode(b64_creds).decode('utf-8')
        creds_dict = json.loads(decoded_str)
        
        # --- VERIFICACIÓN DE INTEGRIDAD DE CLAVE ---
        if 'private_key' not in creds_dict:
            raise ValueError("El JSON no contiene el campo 'private_key'.")
            
        # Corrección de saltos de línea
        creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        
        # Validación estricta del formato PEM
        if not creds_dict['private_key'].startswith("-----BEGIN PRIVATE KEY-----"):
            print("❌ ERROR CRÍTICO: La clave privada decodificada NO tiene el formato válido.")
            print(f"🔍 Empieza con: {creds_dict['private_key'][:50]}...")
            print("🔍 Debería empezar con: -----BEGIN PRIVATE KEY-----")
            print("SOLUCIÓN: Genera un nuevo JSON en Google Cloud y codifícalo en Base64 nuevamente usando el script 'encoder.py'.")
            exit(1)

        print("✅ Clave privada tiene formato válido.")

        # Guardar JSON temporal
        with open('temp_creds.json', 'w') as f:
            json.dump(creds_dict, f)
        
        # Conectar
        gc = gspread.service_account(filename='temp_creds.json')
        sh = gc.open_by_key(SHEET_KEY)
        worksheet = sh.worksheet(SHEET_NAME)
        print("✅ Conexión a Google Sheets exitosa.")

        # Flujo normal
        used_names = get_history_from_sheet(worksheet)
        product = get_random_product(used_names)
        
        if product:
            print(f"🎯 Producto seleccionado: {product['name']}")
            img_file = download_image(product['imageURL'])
            if img_file:
                post_to_reddit_image(product, img_file, worksheet)
                if os.path.exists(img_file): os.remove(img_file)
        else:
            print("😴 No se encontraron productos.")

    except Exception as e:
        import traceback
        print(f"❌ Error inesperado: {e}")
        print(traceback.format_exc())
    
    finally:
        if os.path.exists('temp_creds.json'):
            os.remove('temp_creds.json')
            print("🔒 Archivo temporal eliminado.")
