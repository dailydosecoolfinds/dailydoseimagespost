import requests
import json
import random

# ==========================================
# CONFIGURACIÓN SOVRN
# ==========================================
SOVRN_API_KEY = "134070ee62245f1bfe18f4f36288aa7a"
SOVRN_SECRET = "3077f2bbbca0cf7e5a929176bc6e017b5c10339c"
SOVRN_URL = "https://shopping-gallery.prd-commerce.sovrnservices.com/ai-orchestration/products"
SOVRN_HEADERS = {
    "Authorization": f"secret {SOVRN_SECRET}",
    "Content-Type": "application/json"
}

# ==========================================
# PRUEBA DE AUTOPSIA (VER TODOS LOS PRODUCTOS)
# ==========================================
def diagnose_sovrn():
    print("🔬 MODO DIAGNÓSTICO: Analizando lo que devuelve Sovrn...\n")
    
    query = {"apiKey": SOVRN_API_KEY, "pageUrl": "https://www.youtube.com/@EvateExplica"}
    payload = {"market": "usd_en", "num_products": 20, "exclude_merchants": [], "force_cpr_scoring": False}
    
    r = requests.post(SOVRN_URL, params=query, json=payload, headers=SOVRN_HEADERS)
    
    if r.status_code == 200:
        all_products = r.json()
        
        print(f"📦 Total recibido: {len(all_products)}")
        print("-" * 50)
        
        # Imprimimos los primeros 15 productos SIN FILTRO DE PRECIO
        for i, p in enumerate(all_products[:15], 1):
            name = p.get('name')
            price = p.get('salePrice')
            merchant = p['merchant']['name']
            
            # Marcamos si es caro (>20) o barato
            status = "💰 (CARO)" if float(price) > 20 else "💵 (BARATO)"
            
            print(f"{i}. [{status}] ${price} | {merchant} | {name}")
            
        print("-" * 50)
        print("🧠 ANÁLISIS:")
        caros = [p for p in all_products if float(p.get('salePrice', 0)) > 20]
        baratos = [p for p in all_products if float(p.get('salePrice', 0)) <= 20]
        
        print(f"   Productos CAROS (> $20): {len(caros)}")
        print(f"   Productos BARATOS (<= $20): {len(baratos)}")
        
        if len(caros) == 1 and caros[0]['name'] == "BestOffice Ergonomic Task Chair":
            print("\n❌ DIAGNÓSTICO FINAL:")
            print("El API SOLO tiene UN producto caro (la silla). Todos los demás son baratos.")
            print("El filtro de precio > $20 elige la silla OBLIGATORIAMENTE porque no hay otra opción.")
            print("\nSOLUCIÓN: Bajar el filtro de precio a $10 o cambiar de API.")
        elif len(caros) > 1:
            print("\n❌ DIAGNÓSTICO FINAL:")
            print("Hay más productos caros, pero el API los ordena siempre igual.")
            
    else:
        print("Error de API")

if __name__ == "__main__":
    diagnose_sovrn()
