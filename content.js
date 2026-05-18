// Așteptăm puțin ca pagina să se încarce
setTimeout(() => {
    // Creăm butonul plutitor de protecție
    const scutBtn = document.createElement('button');
    scutBtn.innerHTML = '🛡️ Scut AI: Scanează Mesaje';
    
    // Îi dăm un design frumos care să iasă în evidență peste site
    scutBtn.style.cssText = `
        position: fixed;
        bottom: 25px;
        right: 25px;
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

    // Efect de hover
    scutBtn.addEventListener('mouseover', () => scutBtn.style.transform = 'scale(1.05)');
    scutBtn.addEventListener('mouseout', () => scutBtn.style.transform = 'scale(1)');

    // Ce se întâmplă când dăm click pe buton
    scutBtn.addEventListener('click', () => {
        scutBtn.innerHTML = '⏳ AI analizează discuțiile...';
        scutBtn.disabled = true;
        scutBtn.style.backgroundColor = '#ccc';

        // Luăm tot textul vizibil din chat
        const textDinPagina = document.body.innerText;

        // Îl trimitem către background.js ca să îl dea mai departe la Python
        const extAPI = typeof browser !== "undefined" ? browser : chrome;
        extAPI.runtime.sendMessage({ actiune: "scaneaza_fundal", text: textDinPagina }, (response) => {
            
            // Resetăm butonul
            scutBtn.disabled = false;
            scutBtn.innerHTML = '🛡️ Scut AI: Scanează Mesaje';
            scutBtn.style.backgroundColor = '#f29900';

            // Afișăm rezultatul într-un pop-up pe ecran
            if (response && response.success) {
                alert("🔍 REZULTAT ANALIZĂ AI:\\n\\n" + response.verdict);
            } else {
                alert("❌ Eroare la scanare: " + (response ? response.error : "Eroare necunoscută."));
            }
        });
    });

    // Îl adăugăm pe ecran
    document.body.appendChild(scutBtn);

}, 3000); // Apare la 3 secunde după ce se deschide site-ul