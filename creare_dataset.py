import pandas as pd
from deep_translator import GoogleTranslator
import time
import kagglehub
from kagglehub import KaggleDatasetAdapter

print("=========================================================")
print("🤖 Robotul AI: Descărcare, Traducere și Generare Dataset")
print("=========================================================\n")

fisier_iesire = 'dataset_phishing.csv'

try:
    print("Pasul 1: Descarc baza de date oficială de pe Kaggle...")
    
    df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        "uciml/sms-spam-collection-dataset",
        "spam.csv", 
        pandas_kwargs={'encoding': 'latin-1'}
    )
    
    print("✅ Baza de date a fost descărcată cu succes!")
    
    # Dataset-ul de pe Kaggle are coloanele denumite ciudat ('v1' și 'v2').
    df = df[['v1', 'v2']]
    df.columns = ['eticheta', 'mesaj']
    
    # Transformăm etichetele din engleză în română
    df['eticheta'] = df['eticheta'].map({'ham': 'legitim', 'spam': 'phishing'})
    
    print(f" S-au pregătit {len(df)} mesaje pentru procesare.\n")
    
    # ATENȚIE: Traducerea tuturor celor 5500 de mesaje va dura în jur de 1-2 ore. 
    # Dacă vrei doar un test rapid acum, lasă ".head(1000)" ca să traduci doar primele 1000.
    df_limitat = df.copy()
    
    translator = GoogleTranslator(source='en', target='ro')
    mesaje_traduse = []
    
    print(f"⏳ Pasul 2: Încep traducerea a {len(df_limitat)} mesaje în limba română...")
    print("Acest proces folosește Google Translate API. Te rog așteaptă...\n")
    
    for i, text in enumerate(df_limitat['mesaj']):
        try:
            # Traducem mesajul
            traducere = translator.translate(text)
            mesaje_traduse.append(traducere)
            
            # Afișăm progresul la fiecare 50 de mesaje ca să știi că nu s-a blocat
            if (i + 1) % 50 == 0:
                print(f" -> S-au tradus {i + 1} / {len(df_limitat)} mesaje...")
                
        except Exception as e:
            # Dacă Google dă o eroare temporară, păstrăm mesajul original și continuăm
            mesaje_traduse.append(text)
            time.sleep(1) # Pauză de siguranță

    # Înlocuim textele din engleză cu cele din română
    df_limitat['mesaj'] = mesaje_traduse
    
    # Salvăm rezultatul final pe hard disk!
    df_limitat.to_csv(fisier_iesire, index=False, encoding='utf-8')
    
    print(f"\nSUCCES: '{fisier_iesire}'")
    print("Pasul următor: Rulează 'train_model.py' pentru a-ți antrenare")

except Exception as e:
    print(f"\nA apărut o eroare neașteptată: {str(e)}")