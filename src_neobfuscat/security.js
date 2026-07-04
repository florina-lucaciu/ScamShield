export async function autoVerificare() {
    try {
        // interogăm serverul pentru starea lui și hash-ul oficial
        const resp = await fetch("https://scamshield-docker.onrender.com/verificare-sistem");
        const data = await resp.json();

        if (data.server_integrity !== "OK") {
            alert("⚠️ Eroare de sistem: Serverul central a fost modificat neautorizat!");
            return false;
        }

        // calculăm hash-ul local pentru popup.js
        const response = await fetch(chrome.runtime.getURL('popup.js'));
        const codSursa = await response.text();
        const msgUint8 = new TextEncoder().encode(codSursa);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashLocal = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

        // comparăm cu ce zice serverul
        if (hashLocal !== data.official_popup_hash) {
            alert("🚨 Integritate Compromisă: Codul extensiei tale nu este cel original!");
            return false;
        }

        return true;
    } catch (e) {
        console.error("Eroare verificare:", e);
        return false;
    }
}
