import sys
import json
import struct
import re
import os
import base64
from datetime import datetime
import random

from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
from openai import OpenAI  

from dotenv import load_dotenv

import joblib

from flask import Flask, request, jsonify
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # obține calea absolută a directorului în care se află scriptul
os.chdir(BASE_DIR) # schimbă directorul de lucru curent la BASE_DIR pentru a asigura că toate operațiunile de fișiere se fac în acest director
REPUTATION_DB_PATH = os.path.join(BASE_DIR, "reputation_database.json") # calea către fișierul care conține reputațiile și scorurile
BASELINE_DB_PATH = os.path.join(BASE_DIR, "siteuri_oficiale.json") # calea către fișierul cu "amprentele" site-urilor oficiale
DOMENII_SIGURE_PATH = os.path.join(BASE_DIR, "domenii_sigure.json")

sys.stderr = open(os.path.join(BASE_DIR, "python_errors.log"), "a")

load_dotenv(os.path.join(BASE_DIR, ".env"))
API_KEY_OPENAI = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY_OPENAI)

#def get_message():
#    raw_length = sys.stdin.buffer.read(4)
#    if len(raw_length) == 0:
#        sys.exit(0)
#    message_length = struct.unpack('@I', raw_length)[0]
#    message = sys.stdin.buffer.read(message_length).decode('utf-8')
#    return json.loads(message)

#def send_message(message):
#    content = json.dumps(message).encode('utf-8')
#    sys.stdout.buffer.write(struct.pack('@I', len(content)))
#    sys.stdout.buffer.write(content)
#    sys.stdout.buffer.flush()

def load_reputation_db(): # se încarcă 'baza de date' deja existentă
    if os.path.exists(REPUTATION_DB_PATH):
        try:
            with open(REPUTATION_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def update_reputation_db(db):
    with open(REPUTATION_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

# --- Încărcarea listei cu domenii sigure în memorie ---
def load_trusted_domains():
    if os.path.exists(DOMENII_SIGURE_PATH):
        try:
            with open(DOMENII_SIGURE_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            sys.stderr.write(f"Eroare la citirea domenii_sigure.json: {str(e)}\n")
    
    # Fallback dacă fișierul lipsește
    return {'google.com', 'wikipedia.org', 'github.com', 'upt.ro', 'youtube.com', 'cinemacity.ro', 'emag.ro'}

WHITELIST_GLOBAL = load_trusted_domains()

def simulate_ai_analysis(url): 
    url_lower = url.lower()
    scor_calculat = 0
    status = "verificat"
    
    # extragem domeniul din URL (ex: din "https://www.emag.ro/contact")
    domeniu_curent = urlparse(url_lower).netloc.replace("www.", "")
    
    # Căutăm domeniul în setul global de de site-uri
    if domeniu_curent in WHITELIST_GLOBAL:
        scor_calculat = random.randint(90, 100)
        status = "verificat"
    else:
        # dacă site-ul nu e în lista albă
        cuvinte_suspecte = ['login', 'verify', 'update', 'account', 'secure', 'free', 'crypto', 'password']
        nr_cuvinte_gasite = sum(1 for cuvant in cuvinte_suspecte if cuvant in url_lower)
        
        if nr_cuvinte_gasite >= 2:
            scor_calculat = random.randint(0, 20)
            status = "phishing"
        elif nr_cuvinte_gasite == 1:
            scor_calculat = random.randint(21, 50)
            status = "suspect"
        else:
            scor_calculat = random.randint(51, 89)
            status = "verificat"
    
    if url_lower.startswith("http://"):
        scor_calculat -= 30
        scor_calculat = max(0, scor_calculat)
        if status == "verificat" and scor_calculat <= 50:
            status = "suspect"
            
    return scor_calculat, status


def extrage_caracteristici(url, take_screenshot=False):
    domeniu = urlparse(url).netloc
    caracteristici = {
        "url_vizitat": url,
        "domeniu": domeniu,
        "form_actions": [],
        "iframes_totale": 0,
        "linkuri_moarte": 0,
        "tag_frequency": {"img": 0, "a": 0, "script": 0},
        "certificat_ssl": "Fara conexiune securizata (HTTP)" # certificat
    }
    screenshot_base64 = None
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            #context care imită un utilizator real
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )

            # deschidem un nou tab
            page = browser.new_page()
            
            # răspunsul navigării 
            raspuns = page.goto(url, timeout=30000, wait_until="domcontentloaded") 
            
            # extragem detaliile certificatului (dacă există)
            if raspuns and raspuns.security_details():
                sec_details = raspuns.security_details()
                
                # convertim timestamp-ul (secunde) într-o dată normală
                data_creare = "Necunoscută"
                if sec_details.get('validFrom'):
                    data_creare = datetime.fromtimestamp(sec_details.get('validFrom')).strftime('%Y-%m-%d')
                
                caracteristici["certificat_ssl"] = {
                    "autoritate_emitenta": sec_details.get("issuer"),
                    "creat_la_data": data_creare
                }
            
            # screenshot în memorie dacă este cerut
            if take_screenshot:
                screenshot_buffer = page.screenshot(full_page=True)
                screenshot_base64 = base64.b64encode(screenshot_buffer).decode('utf-8')
            
            # formulare - extragem unde se trimit datele
            formulare = page.locator("form").all()
            for form in formulare:
                actiune = form.get_attribute("action")
                if actiune:
                    caracteristici["form_actions"].append(actiune)
                else:
                    caracteristici["form_actions"].append("fara_actiune_specificata")

            caracteristici["iframes_totale"] = page.locator("iframe").count()

            # link-uri moarte
            linkuri = page.locator("a").all()
            for a in linkuri:
                href = a.get_attribute("href")
                if href in ["#", "javascript:void(0)", ""]:
                    caracteristici["linkuri_moarte"] += 1
            
            caracteristici["tag_frequency"]["img"] = page.locator("img").count()
            caracteristici["tag_frequency"]["a"] = len(linkuri)
            caracteristici["tag_frequency"]["script"] = page.locator("script").count()
            
            browser.close()
    except Exception as e:
        sys.stderr.write(f"Eroare Playwright pt {url}: {str(e)}\n")
        return (None, None) if take_screenshot else None
        
    return (caracteristici, screenshot_base64) if take_screenshot else caracteristici

# ---agentul AI (Vision + Comparație Live) ---
def agent_ai_analiza(url):
    site_uri_oficiale = {}
    if os.path.exists(BASELINE_DB_PATH):
        with open(BASELINE_DB_PATH, "r", encoding="utf-8") as f:
            site_uri_oficiale = json.load(f)
    
    # 1. Extracție site suspect + Screenshot
    rezultat = extrage_caracteristici(url, take_screenshot=True)
    if not rezultat or not rezultat[0]:
        return 0, "eroare", "Nu am putut accesa site-ul sau timpul de încărcare a expirat.", "Niciunul", 0
    date_suspect, base64_image = rezultat
    
    nume_institutie = "NECUNOSCUT"
    site_imitat = "Niciunul"
    incredere_impersonare = 0

    # 2. Vision AI: Identificăm cine este imitat (Cerem direct DOMENIUL)
    domeniu_ai = "necunoscut"
    if base64_image:
        try:
            raspuns_vision = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Privește această imagine a unei pagini web. Ce site oficial încearcă să copieze? Concentrează-te pe LOGO-ul principal din antet (header), ignorând reclamele sau bannerele promoționale mari. Răspunde STRICT cu domeniul web oficial de bază (ex: bancatransilvania.ro, ing.ro, netflix.com, paypal.com). Nu adăuga 'www.' sau 'https://' și nici alte texte. Dacă nu recunoști niciun brand clar, răspunde NECUNOSCUT."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=20 # mai puțini tokeni necesari pentru un simplu domeniu
            )
            domeniu_ai = raspuns_vision.choices[0].message.content.strip().lower()
        except Exception as e:
            sys.stderr.write(f"Eroare Vision AI: {str(e)}\n")

    # 3. Găsim site-ul oficial (după domeniu, nu după nume) și extragem datele
    date_reale = None
    url_oficial_curent = ""
    site_imitat = "Niciunul"

    if domeniu_ai != "necunoscut":
        # Verificăm dacă domeniul există în fișierul nostru local
        for cheie, date in site_uri_oficiale.items():
            if date.get("domeniu_oficial") == domeniu_ai:
                site_imitat = cheie.replace("_", " ").title() # ex: "Ing Bank"
                break
        
        # Chiar dacă exista în fișierul JSON, AI-ul returneaza domeniul
        if site_imitat == "Niciunul":
            site_imitat = domeniu_ai 

        url_oficial_curent = f"https://www.{domeniu_ai}"
        
        date_reale = extrage_caracteristici(url_oficial_curent, take_screenshot=False)

    # generăm data curentă pentru a "trezi" AI-ul la realitate
    data_curenta = datetime.now().strftime("%Y-%m-%d")

    # 4. Promptul Final de Comparație
    prompt = f"""
            Data curentă a sistemului: {data_curenta}
            Analizează acest URL suspect: {url}
            
            Instituție vizată identificată vizual (Logo/Brand): {site_imitat}
            
            Date structurale extrase LIVE de pe site-ul SUSPECT:
            {json.dumps(date_suspect, indent=2)}
            
            Date structurale extrase LIVE de pe site-ul OFICIAL ({url_oficial_curent if url_oficial_curent else 'Niciun profil live generat'}):
            {json.dumps(date_reale, indent=2) if date_reale else 'Nu există date oficiale extrase live pentru comparație.'}
            
            SARCINA TA: 
            1. Compară destinația formularelor (form_actions). Un site legitim trimite datele către propriul domeniu.
            2. Verifică detaliile certificatului SSL (certificat_ssl) luând în considerare DATA CURENTĂ ({data_curenta}). Dacă data emiterii este în trecut, este corect și legitim. Site-urile de phishing folosesc adesea certificate gratuite emise foarte recent (cu 1-3 zile în urmă).
            3. Ignoră "linkurile moarte" dacă numărul de imagini și scripturi sugerează un magazin online modern (acestea folosesc '#' pentru acțiuni JavaScript).
            
            Răspunde OBLIGATORIU în acest format exact:
            VERDICT: [PHISHING / SUSPECT / VERIFICAT]
            SCOR: [0-100, ATENȚIE: 100 înseamnă site complet sigur/legitim, iar 0 înseamnă phishing sever/periculos!]
            SITE_IMITAT: [{site_imitat}]
            INCREDERE_IMPERSONARE: [Gradul de încredere că imită brandul, 0-100]
            MOTIV: [Explicație tehnică clară. Fii concis, max 2-3 propoziții.]
    """
    
    try:
        # folosim modelul avansat pentru o corelare mai bună a JSON-urilor
        raspuns = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Ești un expert tehnic în securitate cibernetică. Răspunde STRICT în formatul cerut, analizând obiectiv JSON-urile cu acțiunile formularelor."},
                      {"role": "user", "content": prompt}]
        )
        text_ai = raspuns.choices[0].message.content

        # Parsare câmpuri din răspuns
        scor = 50
        status = "suspect"
        motiv = text_ai
        incredere = 0

        for linie in text_ai.splitlines():
            linie = linie.strip()
            if linie.startswith("VERDICT:"):
                val = linie.split(":", 1)[1].strip().upper()
                if "PHISHING" in val: status = "phishing"
                elif "SUSPECT" in val: status = "suspect"
                else: status = "verificat"
            elif linie.startswith("SCOR:"):
                try: scor = int(''.join(filter(str.isdigit, linie.split(":", 1)[1])))
                except: pass
            elif linie.startswith("SITE_IMITAT:"):
                site_imitat_extras = linie.split(":", 1)[1].strip()
                if site_imitat_extras and site_imitat_extras.upper() != "NICIUNUL":
                    site_imitat = site_imitat_extras
            elif linie.startswith("INCREDERE_IMPERSONARE:"):
                try: incredere = int(''.join(filter(str.isdigit, linie.split(":", 1)[1])))
                except: pass
            elif linie.startswith("MOTIV:"):
                motiv = linie.split(":", 1)[1].strip()

        return scor, status, motiv, site_imitat, incredere

    except:
        scor, status, motiv = simulate_ai_analysis(url) + ("Eroare la analiza AI avansată. S-a folosit simularea euristică.",)
        return scor, status, motiv, site_imitat, 0


def save_to_json(links):
    try:
        acum = datetime.now()
        an_curent = acum.strftime("%Y")
        luna_curenta = acum.strftime("%m_%B")
        data_zi = acum.strftime("%Y-%m-%d")
        timestamp_complet = acum.strftime("%H:%M:%S")
        cale_folder = os.path.join(BASE_DIR, "logs", an_curent, luna_curenta)
        if not os.path.exists(cale_folder): os.makedirs(cale_folder, exist_ok=True)
        nume_fisier = f"links_{data_zi}.json"
        cale_completa_fisier = os.path.join(cale_folder, nume_fisier)
        date_existente = []
        if os.path.exists(cale_completa_fisier):
            with open(cale_completa_fisier, "r", encoding="utf-8") as f:
                try: date_existente = json.load(f)
                except: date_existente = []
        url_de_azi = {item['url'] for item in date_existente}
        reputatie_globala = load_reputation_db()
        modified_db = False
        verdicte = []
        for link in links:
            if link in reputatie_globala:
                scor_existent = reputatie_globala[link]
                status_verificare = "phishing" if scor_existent <= 20 else "verificat"
                emoji = "✅" if status_verificare == "verificat" else "🚨"
                concluzie = "Site credibil." if scor_existent >= 80 else "Site moderat credibil, procedează cu atenție." if scor_existent >= 50 else "Site suspect, nu introduce date personale!"
                verdicte.append(
                    f"{emoji} {status_verificare.upper()} (din cache)\n"
                    f"Scor credibilitate: {scor_existent}/100\n\n"
                    f"{concluzie}"
                )
            else:
                scor_calculat, status_calculat, motiv, site_imitat, incredere = agent_ai_analiza(link)
                reputatie_globala[link] = scor_calculat
                status_verificare = status_calculat
                modified_db = True

                if link not in url_de_azi:
                    date_existente.append({
                        "ora": timestamp_complet,
                        "url": link,
                        "scor_credibilitate": scor_calculat,
                        "status": status_verificare,
                        "site_imitat": site_imitat,
                        "incredere_impersonare": incredere,
                        "detalii_ai": motiv
                    })
                    url_de_azi.add(link)

                emoji = "✅" if status_calculat == "verificat" else "🚨" if status_calculat == "phishing" else "⚠️"
                concluzie = "Site credibil." if scor_calculat >= 80 else "Site moderat credibil, procedează cu atenție." if scor_calculat >= 50 else "Site suspect, nu introduce date personale!"
                linie_impersonare = ""
                if site_imitat != "Niciunul" and incredere > 0:
                    if status_calculat == "verificat":
                        linie_impersonare = f"\n✅ Brand recunoscut: {site_imitat} ({incredere}% certitudine)\n"
                    else:
                        linie_impersonare = f"\n🎭 Încearcă să imite: {site_imitat} ({incredere}% certitudine)\n"
                
                verdicte.append(
                    f"{emoji} {status_calculat.upper()}\n"
                    f"Scor credibilitate: {scor_calculat}/100"
                    f"{linie_impersonare}\n\n"
                    f"{concluzie}\n\n{motiv}"
                )
        if modified_db: update_reputation_db(reputatie_globala)
        with open(cale_completa_fisier, "w", encoding="utf-8") as f:
            json.dump(date_existente, f, indent=4, ensure_ascii=False)
        return verdicte

    except Exception as e:
        sys.stderr.write(f"Eroare la salvare: {str(e)}\n")
        return [f"Eroare: {str(e)}"]

# --- funcția pentru Chatbot ---
def asistent_chat_phishing(intrebare):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ești un expert în securitate cibernetică integrat într-o extensie de browser. Rolul tău este să educi utilizatorul. Răspunde scurt, la obiect și prietenos DOAR la întrebări legate de phishing, malware, securitate online, parole și protecția datelor. Dacă ești întrebat altceva, refuză politicos."},
                {"role": "user", "content": intrebare}
            ],
            max_tokens=250 # păstrăm răspunsurile scurte
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Eroare de conexiune la asistent: {str(e)}"

# --- Funcția pentru detectarea ingineriei sociale în text ---
#def asistent_analiza_text(text_pagina):
#    try:
        # Tăiem textul la 4000 de caractere ca să nu consumăm prea mulți tokeni (luăm doar textul recent)
#        text_scurt = text_pagina[-4000:] 
        
#        prompt = f"""
#        Analizează acest text vizibil extras dintr-un tab de browser (posibil WhatsApp Web, email, etc.):
#        
#        "{text_scurt}"
        
#        SARCINA:
#        1. Detectează dacă textul conține mesaje de tip phishing/scam (ex: oferte ireale, urgență, cont blocat, colete nesolicitate).
#        2. Extrage orice link suspect găsit în text.
#        
#        RĂSPUNS:
#        Dacă este sigur, răspunde scurt: "✅ Textul paginii pare sigur. Nu am detectat tactici de inginerie socială."
#        Dacă este suspect, răspunde cu un avertisment clar (max 3 propoziții) care să înceapă cu "🚨 ATENȚIE: Am detectat un posibil mesaj de phishing!". Explică ce tactică folosește și îndeamnă utilizatorul să copieze link-ul suspect în scanner-ul extensiei.
#        """
#        
#        response = client.chat.completions.create(
#            model="gpt-4o",
#            messages=[
#                {"role": "system", "content": "Ești un detector de inginerie socială. Analizezi textul brut de pe ecranul utilizatorului."},
#                {"role": "user", "content": prompt}
#            ],
#            max_tokens=250
#        )
#        return response.choices[0].message.content
#    except Exception as e:
#        return f"Eroare la analiza textului: {str(e)}"

# --- Funcția de analiză text bazată pe propriul model ---
def asistent_analiza_text(text_pagina):
    try:
        # tăiem la ultimele 500 de caractere ca să citim doar ultimul mesaj primit
        text_scurt = text_pagina[-500:] 
        
        # 1. Încărcăm modelul antrenat anterior
        cale_model = os.path.join(BASE_DIR, "detector_phishing.pkl")
        if not os.path.exists(cale_model):
            return "❌ Eroare: Modelul AI local lipsește. Rulează train_model.py întâi!"
            
        model_propriu = joblib.load(cale_model)
        
        # 2. prezice statusul textului
        predictie = model_propriu.predict([text_scurt])[0]
        
        # 3. Returnăm rezultatul
        if predictie == 'legitim':
            return "✅ (ML Local) Textul paginii pare sigur. Nu am detectat tactici de inginerie socială."
        else:
            return "🚨 ATENȚIE (ML Local): Modelul nostru de Machine Learning a detectat un posibil mesaj de phishing bazat pe vocabularul folosit! Te rugăm să nu oferi date personale și să copii orice link suspect în scannerul de mai sus."
            
    except Exception as e:
        return f"Eroare la analiza textului ML: {str(e)}"

# --- BUCLA PRINCIPALĂ ---
# while True:
#     received = get_message()
#     
#     tip_actiune = received.get('tip_actiune', 'analiza')
#     text_primit = received.get('text', '').strip()
# 
#     # RAMURA 1: CHAT
#     if tip_actiune == 'chat':
#         raspuns_ai = asistent_chat_phishing(text_primit)
#         send_message({"tip": "chat_response", "echo": raspuns_ai})
#         continue
# 
#     # RAMURA 2: ANALIZĂ TEXT DIN PAGINĂ (Inginerie Socială)
#     if tip_actiune == 'analiza_text':
#         raspuns_text = asistent_analiza_text(text_primit)
#         send_message({"tip": "final", "echo": raspuns_text, "scor_rapid": 50}) # Punem un scor neutru doar pentru UI
#         continue
# 
#     # RAMURA 3: ANALIZĂ LINK (Codul tău existent)
#     if text_primit.startswith("http") or text_primit.startswith("file://"):
#         scor_rapid, status_rapid = simulate_ai_analysis(text_primit)
#         status_ro = "LEGITIM" if status_rapid == "verificat" else status_rapid.upper()
#         
#         mesaj_intermediar = (
#             f"⚡ Analiza rapidă a link-ului:\n"
#             f"După verificarea textului, URL-ul pare a fi {status_ro}.\n\n"
#             f"🤖 Agentul AI descarcă pagina și verifică certificatul SSL...\n"
#             f"⏳ Te rog așteaptă (15-30 secunde)..."
#         )
#         send_message({"tip": "intermediar", "echo": mesaj_intermediar, "scor_rapid": scor_rapid})
# 
#         linkuri_de_procesat = [text_primit]
#         mesaje_ai = save_to_json(linkuri_de_procesat)
#         raspuns_final = "\n".join(mesaje_ai)
#         send_message({"tip": "final", "echo": raspuns_final})
#         
#     else:
#         raspuns = "Pagină invalidă pentru analiză. Te rog deschide un site sau un fișier HTML."
#         send_message({"tip": "final", "echo": raspuns})

# --- INIȚIALIZARE SERVER WEB (API) ---
app = Flask(__name__)
CORS(app) # Permitem extensiei să facă request-uri din browser

@app.route('/', methods=['GET'])
def health_check():
    return "Serverul Scut AI este online!", 200

@app.route('/scaneaza', methods=['POST'])
def scaneaza():
    try:
        # Extragem datele trimise de extensie prin fetch()
        date_primite = request.json
        tip_actiune = date_primite.get('tip_actiune', 'analiza')
        text_primit = date_primite.get('text', '').strip()

        # 1: CHAT
        if tip_actiune == 'chat':
            raspuns_ai = asistent_chat_phishing(text_primit)
            return jsonify({"tip": "chat_response", "echo": raspuns_ai})

        # 2: ANALIZĂ TEXT DIN PAGINĂ
        if tip_actiune == 'analiza_text':
            raspuns_text = asistent_analiza_text(text_primit)
            return jsonify({"tip": "final", "echo": raspuns_text, "scor_rapid": 50})

        # 3: ANALIZĂ LINK
        if tip_actiune == 'analiza':
            if text_primit.startswith("http") or text_primit.startswith("file://"):
                # analiza rapidă
                scor_rapid, status_rapid = simulate_ai_analysis(text_primit)
                
                # analiza cu Playwright și OpenAI
                linkuri_de_procesat = [text_primit]
                mesaje_ai = save_to_json(linkuri_de_procesat)
                raspuns_final = "\n".join(mesaje_ai)
                
                # returnăm direct rezultatul final
                return jsonify({
                    "tip": "final", 
                    "echo": raspuns_final, 
                    "scor_rapid": scor_rapid
                })
            else:
                return jsonify({"tip": "final", "echo": "Pagină invalidă pentru analiză."})

    except Exception as e:
        sys.stderr.write(f"Eroare API: {str(e)}\n")
        return jsonify({"tip": "final", "echo": f"Eroare server Cloud: {str(e)}"})

# --- PORNIRE SERVER ---
if __name__ == "__main__":
    # Render setează automat variabila de mediu PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)