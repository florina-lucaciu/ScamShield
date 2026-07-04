import hashlib

def get_sha256_independent_os(file_path):
    try:
        # 1. Citim fișierul ca text normal
        with open(file_path, "r", encoding="utf-8") as f:
            continut = f.read()
            
        # 2. Normalizăm (înlocuim formatul Windows cu formatul Linux)
        continut_normalizat = continut.replace('\r\n', '\n')
        
        # 3. Transformăm în biți și calculăm hash-ul
        bytes_normalizati = continut_normalizat.encode('utf-8')
        return hashlib.sha256(bytes_normalizati).hexdigest()
    except FileNotFoundError:
        return "Fișier negăsit!"

print(f"Hash app.py:   {get_sha256_independent_os('app.py')}")
print(f"Hash popup.js: {get_sha256_independent_os('popup.js')}")