document.getElementById('send-message-button').addEventListener('click', function () {
    const userInput = document.querySelector('.typing-input').value;
    if (userInput.trim() !== '') {
        displayMessage(userInput, 'user'); // Display user input in the chat
        getBotResponse(userInput);         // Fetch bot response from API
        document.querySelector('.typing-input').value = ''; // Clear the input field
    }
});

// Global server domain (change here or set window.SERVER_DOMAIN before this script runs)
const SERVER = window.SERVER_DOMAIN || 'http://0.0.0.0:10000';

function displayMessage(message, sender) {
    const chatList = document.querySelector('.chat-list');
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', sender);
    messageElement.textContent = message;
    chatList.appendChild(messageElement);
    chatList.scrollTop = chatList.scrollHeight; // Scroll to the bottom
}

async function getBotResponse(input) {
    const chatList = document.querySelector('.chat-list');

    try {
        // POST to the Django server using the global SERVER variable
        const response = await fetch(`${SERVER}/api/sugerir-rae`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: input })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Our endpoint returns plain text (model's final text)
        const text = await response.text();
        displayMessage(text.trim(), 'bot');
    } catch (error) {
        console.error('Error:', error);
        displayMessage('Sorry, something went wrong. Please try again.', 'bot');
    }
}
