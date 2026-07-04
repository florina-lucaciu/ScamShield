import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn import metrics
import joblib
import os

import re

print("==================================================")
print("🛡️ Scut AI - Antrenare pe Dataset Masiv (CSV)")
print("==================================================\n")

# --- FUNCȚIE DE CURĂȚARE - sincronizată cu app.py ---
def curata_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    # Eliminăm link-uri
    text = re.sub(r'http\S+|www\.\S+', ' ', text)
    # Eliminăm caractere speciale și cifre (pentru a rămâne doar cu esența mesajului)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', ' ', text)
    # Eliminăm spații extra
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 1. ÎNCĂRCAREA DATELOR DIN CSV
nume_fisier_csv = 'dataset_phishing.csv' 

if not os.path.exists(nume_fisier_csv):
    print(f"❌ Eroare: Nu găsesc fișierul '{nume_fisier_csv}' în acest folder!")
    print("Asigură-te că ai rulat 'creare_dataset.py' înainte.")
    exit()

print(f"⏳ Citesc baza de date din '{nume_fisier_csv}'...")
# Încărcăm fișierul generat anterior
df = pd.read_csv(nume_fisier_csv)

# Curățăm datele: eliminăm eventualele rânduri goale
df = df.dropna()
print(f"📊 Am încărcat cu succes {len(df)} de mesaje!\n")

# 2. PREGĂTIREA DATELOR
# Extragem coloanele în variabilele X (textul) și y (răspunsul corect)
print("⏳ Preprocesez mesajele pentru antrenare...")
df['mesaj_curat'] = df['mesaj'].apply(curata_text)

X = df['mesaj_curat']
y = df['eticheta']

# Împărțim datele: 80% pentru învățare, 20% pentru a-l testa 
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Pipeline
model = Pipeline([
    ('vectorizator', TfidfVectorizer(
        ngram_range=(1, 2), 
        max_features=5000, # Limităm la cele mai importante 5000 de cuvinte
        sublinear_tf=True   # Ajută la reducerea impactului cuvintelor care apar prea des
    )), 
    ('clasificator', MultinomialNB(alpha=0.1)) # Alpha mic ajută la detectarea termenilor rari (phishing)
])

# 4. ANTRENAREA
print(f"⏳ Antrenez modelul de Machine Learning pe {len(X_train)} de mesaje...")
model.fit(X_train, y_train)
print("✅ Antrenare finalizată cu succes!\n")

# 5. TESTAREA 
print(f"⏳ Testez modelul pe restul de {len(X_test)} mesaje nevăzute până acum...")
predictii = model.predict(X_test)

acuratete = metrics.accuracy_score(y_test, predictii)
print(f"🎯 Acuratețea modelului tău este: {acuratete * 100:.2f}%\n")

# Afișăm un raport 
print("Raport detaliat de clasificare:")
print(metrics.classification_report(y_test, predictii))

# 6. SALVAREA MODELULUI
nume_model = 'detector_phishing.pkl'
joblib.dump(model, nume_model)
print(f"\n📁 Noul model antrenat masiv a fost salvat ca '{nume_model}'.")
print("Extensia ta folosește acum un AI profesionist!")