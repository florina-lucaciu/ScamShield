const extAPI = typeof browser !== "undefined" ? browser : chrome;

// Ascultăm mesajele venite de la butonul din aplicatia de mesagerie
extAPI.runtime.onMessage.addListener((request, sender, sendResponse) => {
    
    if (request.actiune === "scaneaza_fundal") {
        
        // URL-ul serverului Render
        const URL_SERVER = "https://scamshield-docker.onrender.com/scaneaza";

        // o funcție asincronă pentru a contacta API-ul
        async function contacteazaCloud() {
            try {
                const raspunsServer = await fetch(URL_SERVER, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ 
                        tip_actiune: "analiza_text", 
                        text: request.text 
                    })
                });

                if (!raspunsServer.ok) {
                    throw new Error(`Eroare HTTP: ${raspunsServer.status}`);
                }

                const response = await raspunsServer.json();

                if (response.tip === "final") {
                    // trimitem răspunsul dat după analiza modelului local înapoi în fereastra de chat
                    sendResponse({ success: true, verdict: response.echo });
                }
            } catch (error) {
                // în caz de eroare (pică netul sau e oprit serverul)
                sendResponse({ success: false, error: "Eroare conexiune Cloud: " + error.message });
            }
        }

        // funcția asincronă
        contacteazaCloud();

        // true pentru a ține canalul deschis până răspunde AI-ul
        return true; 
    }
});
