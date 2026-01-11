let lastIntent = "";
let lastSpokenTime = 0;

function speak(text) {
    // Debounce: Prevent speaking too fast (wait 2 seconds between words)
    const now = Date.now();
    if (now - lastSpokenTime < 2000) return; 

    // Browser Native TTS
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1; 
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
    
    // Update UI log
    document.getElementById('last-spoken').innerText = text;
    lastSpokenTime = now;
}

function updateStatus() {
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            const intentDisplay = document.getElementById('intent-display');
            const currentIntent = data.intent;

            // Update the big text
            intentDisplay.innerText = currentIntent;

            // Logic: Only speak if the intent is new and meaningful
            if (currentIntent !== lastIntent && 
                currentIntent !== "Listening..." && 
                currentIntent !== "Unknown") {
                
                speak(currentIntent);
                lastIntent = currentIntent;
            }
        })
        .catch(error => console.error('Error:', error));
}

// Check for updates every 500 milliseconds
setInterval(updateStatus, 500);