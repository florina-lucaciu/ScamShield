const extAPI = typeof browser !== "undefined" ? browser : chrome;

document.addEventListener('DOMContentLoaded', async () => {

    // import pentru evitarea erorilor de la obfuscarea codului și pentru a verifica integritatea extensiei
    const modulSecuritate = await import('./security.js');
    const autoVerificare = modulSecuritate.autoVerificare;

    const sistemIntegru = await autoVerificare();
    if (!sistemIntegru) {
        document.body.innerHTML = "<h2 style='color:red; text-align:center;'>⚠️ Acces Blocat: Probleme de Integritate</h2>";
        return;
    }
    
    // --- 1. LOGICA PENTRU SCHIMBAREA TAB-URILOR ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // --- 2. ELEMENTE PENTRU SCANARE LINK ---
    const urlInput = document.getElementById('urlInput');
    const inputErrorDiv = document.getElementById('inputError');
    const scanBtn = document.getElementById('scanUrlBtn');
    const sendBtn = document.getElementById('sendBtn');
    const responseDiv = document.getElementById('response');
    const scanTextBtn = document.getElementById('scanTextBtn');
    
    // --- 3. ELEMENTE PENTRU CHAT ---
    const chatInput = document.getElementById('chatInput');
    const sendChatBtn = document.getElementById('sendChatBtn');
    const chatHistory = document.getElementById('chatHistory');

    // --- FUNCȚIE PENTRU FORMATĂREA TEXTULUI AI (MARKDOWN -> HTML) ---
    function formateazaTextAI(text) {
        if (!text) return "";
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') 
            .replace(/\*(.*?)\*/g, '<em>$1</em>');            
    }

    urlInput.addEventListener('input', () => {
        inputErrorDiv.style.display = "none";
    });

    // --- 4. FUNCȚIA DE COMUNICARE CU PYTHON ---
    async function trimiteMesajCatrePython(tip_actiune, text) {
        if (tip_actiune === 'analiza') {
            let domeniuCurent = text;
            try { 
                domeniuCurent = new URL(text).hostname.replace("www.", ""); 
            } catch(e) {}

            let rezultatLocal = await extAPI.storage.local.get({ domeniiSigure: [] });
            
            if (rezultatLocal.domeniiSigure.includes(domeniuCurent)) {
                responseDiv.style.borderLeft = "6px solid #188038";
                responseDiv.style.backgroundColor = "#e6f4ea";
                responseDiv.innerText = "✅ VERIFICAT (Listă Locală)\nScor credibilitate: 100/100\n\nAcest domeniu a fost marcat ca sigur de tine în setările extensiei.";
                return;
            }
        }

        if (tip_actiune === 'analiza' || tip_actiune === 'analiza_text') {
            sendBtn.disabled = true;
            scanBtn.disabled = true;
            scanTextBtn.disabled = true;
            sendBtn.innerText = "⏳ Analiză Cloud...";
            responseDiv.style.borderLeft = "4px solid #0060df";
            responseDiv.style.backgroundColor = "white";
            responseDiv.innerText = "🤖 Agentul AI analizează textul extras pentru a detecta tactici de inginerie socială...\n⏳ Te rog așteaptă...";
        } else if (tip_actiune === 'chat') {
            sendChatBtn.disabled = true;
            sendChatBtn.innerText = "...";
            chatHistory.innerHTML += `<div class="chat-msg msg-user">${text}</div>`;
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        const URL_SERVER = "https://scamshield-docker.onrender.com/scaneaza"; 

        try {
            const raspunsServer = await fetch(URL_SERVER, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tip_actiune: tip_actiune, text: text })
            });

            if (!raspunsServer.ok) throw new Error(`Eroare HTTP: ${raspunsServer.status}`);
            
            const response = await raspunsServer.json();

            if (response.tip === "chat_response") {
                sendChatBtn.disabled = false;
                sendChatBtn.innerText = "Întreabă";
                const typingInd = document.getElementById('typingIndicator');
                if(typingInd) typingInd.remove();
                chatHistory.innerHTML += `<div class="chat-msg msg-ai">${formateazaTextAI(response.echo)}</div>`;
                salveazaIstoricChat();
            } 
            else {
                let textCurat = formateazaTextAI(response.echo);
                let verdict = textCurat.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');

                let scor = response.scor_rapid !== undefined ? response.scor_rapid : 50;

                if (scor >= 80) {
                    responseDiv.style.borderLeft = "6px solid #188038";
                    responseDiv.style.backgroundColor = "#e6f4ea";
                } else if (scor >= 50) {
                    responseDiv.style.borderLeft = "6px solid #f29900";
                    responseDiv.style.backgroundColor = "#fef7e0";
                } else {
                    responseDiv.style.borderLeft = "6px solid #d93025";
                    responseDiv.style.backgroundColor = "#fce8e6";
                }
                
                responseDiv.innerText = verdict;
                
                sendBtn.disabled = false;
                scanBtn.disabled = false;
                scanTextBtn.disabled = false; 
                scanTextBtn.innerText = "Citește Textul Paginii";
                sendBtn.innerText = "Scanează Link-ul Curent";
            }

        } catch (error) {
            if (tip_actiune === 'analiza' || tip_actiune === 'analiza_text') {
                responseDiv.innerText = "❌ Eroare conexiune server Cloud: " + error.message;
                responseDiv.style.borderLeft = "6px solid #d93025";
                responseDiv.style.backgroundColor = "#fce8e6";
                sendBtn.disabled = false;
                scanBtn.disabled = false;
                scanTextBtn.disabled = false;
                scanTextBtn.innerText = "Citește Textul Paginii";
                sendBtn.innerText = "Scanează Tab-ul Curent";
            } else if (tip_actiune === 'chat') {
                const typingInd = document.getElementById('typingIndicator');
                if(typingInd) typingInd.remove();
                sendChatBtn.disabled = false;
                sendChatBtn.innerText = "Întreabă";
            }
        }
    }

    // --- 5. EVENIMENTE BUTOANE ---
    
    scanBtn.addEventListener('click', () => {
        const url = urlInput.value.trim();
        if (!url) {
            inputErrorDiv.innerText = "⚠️ Introdu un URL în câmpul de mai sus.";
            inputErrorDiv.style.display = "block";
            return;
        }
        if (!url.startsWith("http") && !url.startsWith("file://")) {
            inputErrorDiv.innerText = "⚠️ URL-ul trebuie să înceapă cu http:// sau https://";
            inputErrorDiv.style.display = "block";
            return;
        }
        inputErrorDiv.style.display = "none";
        responseDiv.style.display = "block";
        trimiteMesajCatrePython('analiza', url);
    });

    sendBtn.addEventListener('click', async () => {
        try {
            responseDiv.style.display = "block";
            let [tab] = await extAPI.tabs.query({ active: true, currentWindow: true });
            trimiteMesajCatrePython('analiza', tab.url);
        } catch (error) {
            responseDiv.innerText = "❌ Eroare extensie: " + error.message;
        }
    });

    // --- LOGICA MULTI-SERVICIU (LEGĂTURA CU CONTENT.JS) ---
    scanTextBtn.addEventListener('click', async () => {
        try {
            let [tab] = await extAPI.tabs.query({ active: true, currentWindow: true });
            
            sendBtn.disabled = true;
            scanBtn.disabled = true;
            scanTextBtn.disabled = true;
            scanTextBtn.innerText = "⏳ Se cere textul...";
            responseDiv.style.display = "block";

            // se trimite un "ping" către content.js injectat în pagină
            extAPI.tabs.sendMessage(tab.id, { actiune: "da_mi_textul" }, (response) => {
                
                // se verifică dacă content.js a răspuns și dacă a găsit ceva
                if (extAPI.runtime.lastError || !response || !response.textExtras || response.textExtras.length < 3) {
                    responseDiv.style.display = "block";
                    responseDiv.innerText = "❌ Nu am putut extrage text valid. Încearcă să selectezi textul manual cu mouse-ul și apasă din nou.";
                    scanTextBtn.disabled = false;
                    scanTextBtn.innerText = "Citește Textul Paginii";
                    sendBtn.disabled = false;
                    scanBtn.disabled = false;
                    return;
                }

                // dacă s-a primit textul de la content.js, se trimite la Python
                trimiteMesajCatrePython('analiza_text', response.textExtras);
            });

        } catch (error) {
            responseDiv.style.display = "block";
            responseDiv.innerText = "❌ Eroare sistem: " + error.message;
            scanTextBtn.disabled = false;
            scanTextBtn.innerText = "Citește Textul Paginii";
            sendBtn.disabled = false;
            scanBtn.disabled = false;
        }
    });

    // Buton Trimitere Chatbot
    sendChatBtn.addEventListener('click', () => {
        const intrebare = chatInput.value.trim();
        if (!intrebare) return;

        chatInput.value = ""; // Golim căsuța de text imediat după ce am salvat întrebarea

        // Lăsăm funcția trimiteMesajCatrePython să se ocupe singură de desenarea mesajului și de scroll!
        trimiteMesajCatrePython('chat', intrebare);
    });

    chatInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') sendChatBtn.click();
    });
    
    urlInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') scanBtn.click();
    });

    // --- 6. GESTIONARE WHITELIST LOCAL ---
    const inputWhitelist = document.getElementById('input-whitelist');
    const btnAdaugaWhitelist = document.getElementById('btn-adauga-whitelist');
    const listaWhitelist = document.getElementById('lista-whitelist');

    function incarcaWhitelist() {
        extAPI.storage.local.get({ domeniiSigure: [] }).then((rezultat) => {
            if (!listaWhitelist) return;
            listaWhitelist.innerHTML = ''; 
            
            rezultat.domeniiSigure.forEach(domeniu => {
                let li = document.createElement('li');
                li.textContent = domeniu + " ";
                
                let btnSterge = document.createElement('button');
                btnSterge.textContent = "❌";
                btnSterge.style = "background: none; border: none; cursor: pointer; font-size: 10px;";
                btnSterge.onclick = () => stergeDomeniu(domeniu);
                
                li.appendChild(btnSterge);
                listaWhitelist.appendChild(li);
            });
        });
    }

    if (btnAdaugaWhitelist) {
        btnAdaugaWhitelist.addEventListener('click', () => {
            let domeniuBrut = inputWhitelist.value.trim().toLowerCase();
            if (!domeniuBrut) return;

            try {
                if (domeniuBrut.startsWith('http')) {
                    domeniuBrut = new URL(domeniuBrut).hostname;
                }
            } catch(e) {}
            
            let domeniuCurat = domeniuBrut.replace("www.", "");

            extAPI.storage.local.get({ domeniiSigure: [] }).then((rezultat) => {
                let domenii = rezultat.domeniiSigure;
                if (!domenii.includes(domeniuCurat)) {
                    domenii.push(domeniuCurat);
                    extAPI.storage.local.set({ domeniiSigure: domenii }).then(() => {
                        inputWhitelist.value = ''; 
                        incarcaWhitelist(); 
                    });
                }
            });
        });
    }

    function stergeDomeniu(domeniuDeSters) {
        extAPI.storage.local.get({ domeniiSigure: [] }).then((rezultat) => {
            let domeniiNoi = rezultat.domeniiSigure.filter(d => d !== domeniuDeSters);
            extAPI.storage.local.set({ domeniiSigure: domeniiNoi }).then(() => {
                incarcaWhitelist();
            });
        });
    }

    incarcaWhitelist();

    // --- 7. TOGGLE PENTRU MENIURI (SETĂRI & INFO) ---
    const btnToggleSetari = document.getElementById('btn-toggle-setari');
    const sectiuneSetari = document.getElementById('sectiune-setari');
    const btnToggleInfo = document.getElementById('btn-toggle-info');
    const sectiuneInfo = document.getElementById('sectiune-info');
    const meniuTaburi = document.querySelector('.tabs');
    const containerPrincipal = document.querySelector('.tab-container');

    if (btnToggleSetari && sectiuneSetari && btnToggleInfo && sectiuneInfo) {
        btnToggleSetari.addEventListener('click', () => {
            if (sectiuneSetari.style.display === 'none') {
                sectiuneSetari.style.display = 'block';
                btnToggleSetari.style.transform = 'rotate(90deg)';
                sectiuneInfo.style.display = 'none';
                btnToggleInfo.style.transform = 'scale(1)';
                meniuTaburi.style.display = 'none';
                containerPrincipal.style.display = 'none';
            } else {
                sectiuneSetari.style.display = 'none';
                btnToggleSetari.style.transform = 'rotate(0deg)';
                meniuTaburi.style.display = 'flex';
                containerPrincipal.style.display = 'block';
            }
        });

        btnToggleInfo.addEventListener('click', () => {
            if (sectiuneInfo.style.display === 'none') {
                sectiuneInfo.style.display = 'block';
                btnToggleInfo.style.transform = 'scale(1.1)'; 
                sectiuneSetari.style.display = 'none';
                btnToggleSetari.style.transform = 'rotate(0deg)';
                meniuTaburi.style.display = 'none';
                containerPrincipal.style.display = 'none';
            } else {
                sectiuneInfo.style.display = 'none';
                btnToggleInfo.style.transform = 'scale(1)';
                meniuTaburi.style.display = 'flex';
                containerPrincipal.style.display = 'block';
            }
        });
    }

    // --- 8. SALVARE ȘI ÎNCĂRCARE ISTORIC CHAT ---
    const btnStergeChat = document.getElementById('btn-sterge-chat');
    const mesajDefaultChat = `<div class="chat-msg msg-ai">Salut! Sunt asistentul tău personal de securitate cibernetică. Mă poți întreba orice legat de phishing, parole sigure sau protecția datelor!</div>`;

    function incarcaIstoricChat() {
        extAPI.storage.local.get({ istoricChat: null }).then((rezultat) => {
            if (rezultat.istoricChat) {
                chatHistory.innerHTML = rezultat.istoricChat;
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }
        });
    }

    function salveazaIstoricChat() {
        extAPI.storage.local.set({ istoricChat: chatHistory.innerHTML });
    }

    if (btnStergeChat) {
        btnStergeChat.addEventListener('click', () => {
            extAPI.storage.local.remove('istoricChat').then(() => {
                chatHistory.innerHTML = mesajDefaultChat;
            });
        });
    }

    incarcaIstoricChat();
});
