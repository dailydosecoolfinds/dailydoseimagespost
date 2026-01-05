    # 1. CONEXIÓN GOOGLE SHEETS (FIX DEFINITIVO: ESCAPADO AGRESIVO)
    google_json_str = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    if not google_json_str:
        print("❌ ERROR: No se encontró el secreto.")
        exit()
    
    try:
        # ----------------------------------------------------
        # FIX: Escapado de saltos de línea para archivos de texto
        # GitHub a veces inyecta saltos de línea reales (\n) que rompen el JSON.
        # Forzamos a que TODO sea texto plano con escaped newlines (\n).
        # 1. Eliminamos todos los saltos reales (\r y \n) por si acaso.
        # 2. Reemplazamos por escaped newlines (\\n).
        print("✅ Normalizando formato de saltos de línea...")
        clean_json_str = google_json_str.replace('\r', '').replace('\n', '\\n')
        
        # Ahora parseamos el JSON "limpio"
        creds_dict = json.loads(clean_json_str)
        
        # Y lo escribimos al archivo. json.dump pondrá los escapes correctos.
        with open('temp_creds.json', 'w') as f:
            json.dump(creds_dict, f)
        # ----------------------------------------------------
            
        # Conectar usando el archivo generado
        gc = gspread.service_account(filename='temp_creds.json')
        sh = gc.open_by_key(SHEET_KEY)
        worksheet = sh.worksheet(SHEET_NAME)
        print("✅ Conexión Google Sheets exitosa.")
        
    except Exception as e:
        print(f"❌ Fatal: No se pudo conectar a Google Sheet: {e}")
        exit()
