
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



// document.addEventListener('DOMContentLoaded', function() {
//     // Capture RFID input
//     document.addEventListener('keyup', function(event) {
//         if (event.key === 'Enter') {
//             const rfidTag = event.key; // Capture the RFID tag
//             console.alert(rfidTag)
//             //sendToBackend(rfidTag);
//         }
//     });

//     // Handle submit button click
//     document.getElementById('submit-button').addEventListener('click', function() {
//         const uniqueId = document.getElementById('unique-id').value;
//         sendToBackend(uniqueId);
//     });

//     function sendToBackend(id) {
//         fetch('/api/login/', {  // URL to your Django API endpoint
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//             },
//             body: JSON.stringify({ id: id }),
//         })
//         .then(response => {
//             if (!response.ok) {
//                 throw new Error('Network response was not ok');
//             }
//             return response.json();
//         })
//         .then(data => {
//             console.log('Response from backend:', data);
//             // Handle successful login response
//         })
//         .catch(error => {
//             console.error('Error sending ID:', error);
//             // Handle error response
//         });
//     }
// });