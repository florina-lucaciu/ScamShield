const extAPI = typeof browser !== "undefined" ? browser : chrome;

function extrageTextSimplu() {
    // dacă utilizatorul a selectat ceva, luăm selecția
    let textSelectat = window.getSelection().toString().trim();
    if (textSelectat.length > 5) {
        return textSelectat;
    }
    
    // dacă nu e nimic selectat, luăm TOT textul de pe ecran
    return document.body.innerText;
}


// butonul plutitor (care apare in pagină)
setTimeout(() => {
    const scutBtn = document.createElement('button');
    scutBtn.innerHTML = '🛡️ Scut AI: Scanează Mesaje';
    
    scutBtn.style.cssText = `
        position: fixed;
        top: 75px; 
        right: 40px;
        z-index: 9999999;
        background-color: #f29900;
        color: #111;
        border: 2px solid white;
        padding: 12px 18px;
        border-radius: 30px;
        font-weight: bold;
        font-family: 'Segoe UI', Tahoma, sans-serif;
        font-size: 14px;
        cursor: pointer;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        transition: transform 0.2s, background-color 0.2s;
    `;

    scutBtn.addEventListener('mouseover', () => scutBtn.style.transform = 'scale(1.05)');
    scutBtn.addEventListener('mouseout', () => scutBtn.style.transform = 'scale(1)');

    scutBtn.addEventListener('click', () => {
        scutBtn.innerHTML = '⏳ AI analizează discuțiile...';
        scutBtn.disabled = true;
        scutBtn.style.backgroundColor = '#ccc';

        const textDeScanat = extrageTextSimplu();

        extAPI.runtime.sendMessage({ actiune: "scaneaza_fundal", text: textDeScanat }, (response) => {
            scutBtn.disabled = false;
            scutBtn.innerHTML = '🛡️ Scut AI: Scanează Mesaje';
            scutBtn.style.backgroundColor = '#f29900';

            if (response && response.success) {
                alert("🔍 REZULTAT ANALIZĂ AI:\n\n" + response.verdict);
            } else {
                alert("❌ Eroare la scanare: " + (response ? response.error : "Eroare necunoscută."));
            }
        });
    });

    document.body.appendChild(scutBtn);
}, 3000); 


// legătura cu extensia (cu butonul din popup.js)
extAPI.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.actiune === "da_mi_textul") {
        
        // trimitem exact același text pe care l-am scanat și în butonul plutitor, ca să fie disponibil și în popup
        const textDeScanat = extrageTextSimplu();
        
        // trimitem înapoi textul, limitat la 3000 de caractere pentru a nu supraîncărca serverul
        sendResponse({ textExtras: textDeScanat.substring(0, 3000) });
    }
    return true; 
});