function homePage(){
    window.location.href = '/eonpod/';
}

// Function to scroll to the end of the content inside a div
function scrollToBottom() {
    var conversationHistory = document.getElementById("chat-cardbody");
    conversationHistory.scrollTop = conversationHistory.scrollHeight;
    console.log("scrolling to bottom");
}

var dotsAnimation = document.getElementById('wave');
function startAnimation() {
    dotsAnimation.style.display = 'inline'; // Make the animation visible
}

function stopAnimation() {
    dotsAnimation.style.display = 'none';
}

document.getElementById('promptForm').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent default form submission
    var question = document.getElementById('question').value;
    document.getElementById('conversationHistory').innerHTML += '<span style="color: red; font-weight: bold; font-size:30px">' + question + '</span><br>';
    setTimeout(scrollToBottom, 100);
    startAnimation();
    const formData = new FormData(this);
    fetch('/generate_response/', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
    document.getElementById('question').value = ''; // Clear input value
    stopAnimation();
    
    // Convert newlines to <br> tags for proper HTML rendering
    const formattedResponse = data.response.replace(/\n/g, '<br>');
    
    // Insert the formatted response into the conversation history
    document.getElementById('conversationHistory').innerHTML += 
        '<span style="color: black; font-size:30px">' + formattedResponse + '</span><br><hr>';
    
    setTimeout(scrollToBottom, 100);
})
    .catch(error => console.error('Error:', error));
});

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

document.addEventListener("DOMContentLoaded", function() {
// Assuming a button with ID "fullscreenButton" triggers full screen mode
const fullscreenButton = document.getElementById("fullscreenButton");
const fullscreenExitButton = document.getElementById("fullscreenExitButton");

    if (fullscreenButton) {
        fullscreenButton.addEventListener("click", function() {
            fullscreenButton.style.display = 'none'
            fullscreenExitButton.style.display = 'block'
            requestFullScreen();
        });  
    }

    if (fullscreenExitButton) {
        fullscreenExitButton.addEventListener("click", function() {
            fullscreenButton.style.display = 'block'
            fullscreenExitButton.style.display = 'none'
            exitFullScreen();
        });  
    }
});
