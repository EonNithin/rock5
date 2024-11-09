
const pinInput = document.getElementById('pin');
const keys = document.querySelectorAll('.key');
const clearButton = document.querySelector('.key-clear');

keys.forEach(key => {
    key.addEventListener('click', () => {
        if (pinInput.value.length < 6) {
            pinInput.value += key.innerText;
        }
    });
});

clearButton.addEventListener('click', () => {
    pinInput.value = '';
});

// Add an event listener to the document that will refocus the pin input on each click
document.addEventListener('click', (event) => {
    // Check if the clicked element is not the pin input
    if (event.target !== pinInput) {
        pinInput.focus(); // Refocus the input
    }
});