
let isConnected = false;
let isRecording = false;
let isStreaming = false;


document.addEventListener('DOMContentLoaded', function() {
    const logoutButton = document.getElementById('logout');
    
    if (logoutButton) {
        logoutButton.addEventListener('click', logoutFunction);
    }
});

function logoutFunction() {
    // Redirect to the login page or any other logic for logout
    window.location.href = '/login_page/';
}

window.addEventListener('unload', async function (event) {
    console.log('Window is closing, sending fetch request...');
    alert("You are leaving the window... Recording will be autosaved")
    // Trigger fetch request when the window is unloading
    try {
        let response = await fetch('/stop_recording_view/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        console.log('Fetch request sent successfully on unload');
    } catch (error) {
        console.error('Error during fetch request:', error);
    }
});

// Add event listener for DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if the username is present and the welcome message exists
    var messageElement = document.getElementById('welcome-message');
    
    // Correctly logging messageElement instead of welcomeElement
    console.log(messageElement); 
    
    if (messageElement) {
        console.log("Welcome message element found:", messageElement);
        // Set timeout to hide the welcome message after 5 seconds
        setTimeout(function() {
            console.log("Timeout function triggered");
            messageElement.style.display = 'none';
        }, 5000); // 5000 milliseconds = 5 seconds
    }
});

// Function to update the status and SVG fill colors
function updateStatus(data) {
    // // // Update the status messages
    // document.getElementById('mic-status').innerText = data.mic_status ? 'True' : 'False';
    // document.getElementById('video-status').innerText = data.camera_status ? 'True' : 'False';
    // document.getElementById('screen-capture-status').innerText = data.screen_capture_status ? 'True' : 'False';

    // Update SVG fill colors based on status
    document.getElementById('mic').setAttribute('fill', data.mic_status ? '#a9dfbf' : '#f8c471');
    document.getElementById('camera').setAttribute('fill', data.camera_status ? '#a9dfbf' : '#f8c471');
    document.getElementById('screen-capture').setAttribute('fill', data.screen_capture_status ? '#a9dfbf' : '#f8c471');
}

// Function to check device connections
async function checkDeviceConnections() {
    try {
        let response = await fetch('/check_device_connections/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        if (response.ok) {
            // Assuming the response is JSON and contains status fields
            let data = await response.json();
            console.log(data);
            updateStatus(data);
        } else {
            console.error('Response error:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('Error during fetch request:', error);
    }
}

// Add event listener for DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initial check
    checkDeviceConnections();
    // Set interval to check device connections every minute (60000 milliseconds)
    // setInterval(checkDeviceConnections, 60000);
});


// Function to get the CSRF token
function getCookie(name) {
   let cookieValue = null;
   if (document.cookie && document.cookie !== '') {
       const cookies = document.cookie.split(';');
       for (let i = 0; i < cookies.length; i++) {
           const cookie = cookies[i].trim();
           // Does this cookie string begin with the name we want?
           if (cookie.substring(0, name.length + 1) === (name + '=')) {
               cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
               break;
           }
       }
   }
   return cookieValue;
}


// Function to toggle recording state
async function toggleRecording() {
    const controlsDiv = document.getElementById('controls');
    const startRecordButton = document.getElementById("startRecord");
    const stopRecordButton = document.getElementById("stopRecord");
    const textLabelRecord = document.getElementById("text-label-record");
    const progressBar = document.getElementById("progress-bar1");
    
    if (isRecording) {
        // Stop recording
        try {
            // Show a confirm dialog instead of an alert
            // Call this function instead of using `confirm()`
            showConfirmDialog();
        } catch (error) {
            console.error('Failed to stop recording:', error);            
        }
    } else {
        // Check if a subject is selected
        if (!selectedSubject) {
            alert('Please select subject to start recording.');
            return;
        }

        // Start recording
        try {
            controlsDiv.style.display = 'block';
            startRecordButton.style.display = "none";
            stopRecordButton.style.display = "block";
            textLabelRecord.textContent = "Stop Recording";
            progressBar.style.visibility = "visible"; // Show progress bar
            isRecording = true;

            // Call your start recording function here
            let startRecordingResponse = await fetch('/start_recording_view/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ subject: selectedSubject }) // Send selectedSubject as part of the request body
            });

            let startRecordingData = await startRecordingResponse.json();
            console.log("start recording view response",startRecordingData.message);
        
        } catch (error) {
            console.error('Failed to start recording:', error);
        }
    }
}

// Handling dropdown select subject

let selectedSubject = '';


function toggleDropdown() {
   document.getElementById("dropdown-content").classList.toggle("show");
}


function selectOption(option) {
   const dropdownLabel = document.getElementById("dropdown-label").children[0];
   if (dropdownLabel) {
       dropdownLabel.textContent = option;
       selectedSubject = option; // Store the selected option
       console.log(selectedSubject);
   } else {
       console.error('Dropdown label element not found.');
   }
   document.getElementById("dropdown-content").classList.remove("show");
}


// Close the dropdown if the user clicks outside of it
window.onclick = function(event) {
   if (!event.target.matches('.custom-dropdown-label') && !event.target.matches('.custom-dropdown-label *')) {
       const dropdowns = document.getElementsByClassName("dropdown-content");
       for (let i = 0; i < dropdowns.length; i++) {
           const openDropdown = dropdowns[i];
           if (openDropdown.classList.contains('show')) {
               openDropdown.classList.remove('show');
           }
       }
   }
}


function showSettings(){
   console.log("clicked settings icon");
   const settings = document.getElementById('settings');
   if (settings.style.display === 'none' || settings.style.display === '') {
       settings.style.display = 'block';
   } else {
       settings.style.display = 'none';
   }
}


document.addEventListener('click', function(event) {
   const gearIcon = document.getElementById('gear-icon');
   const settings = document.getElementById('settings');
   if (!gearIcon.contains(event.target)) {
       settings.style.display = 'none';
   }
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

