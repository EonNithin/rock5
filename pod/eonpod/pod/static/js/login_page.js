
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

