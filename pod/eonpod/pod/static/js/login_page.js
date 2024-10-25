
// Function to request full screen mode
function requestFullScreen() {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
        elem.requestFullscreen();
    } else if (elem.mozRequestFullScreen) { /* Firefox */
        elem.mozRequestFullScreen();
    } else if (elem.webkitRequestFullscreen) { /* Chrome, Safari and Opera */
        elem.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
    } else if (elem.msRequestFullscreen) { /* IE/Edge */
        elem.msRequestFullscreen();
    }
}

// Function to request exit full screen mode
function exitFullScreen() {
    const elem = document;
    if (elem.exitFullscreen) {
        elem.exitFullscreen();
    } else if (elem.mozCancelFullScreen) { /* Firefox */
        elem.mozCancelFullScreen();
    } else if (elem.webkitExitFullscreen) { /* Chrome, Safari and Opera */
        elem.webkitExitFullscreen();
    } else if (elem.msExitFullscreen) { /* IE/Edge */
        elem.msExitFullscreen();
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const fullscreenButton = document.getElementById("fullscreenButton");
    const fullscreenExitButton = document.getElementById("fullscreenExitButton");
    console.log("identified fullscreen and exit fullscreen buttons successfully")
    if (fullscreenButton && fullscreenExitButton) {
        fullscreenButton.addEventListener("click", function () {
            fullscreenButton.style.display = 'none';
            fullscreenExitButton.style.display = 'block';
            requestFullScreen();
        });

        fullscreenExitButton.addEventListener("click", function () {
            fullscreenButton.style.display = 'block';
            fullscreenExitButton.style.display = 'none';
            exitFullScreen();
        });
    }
});


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

