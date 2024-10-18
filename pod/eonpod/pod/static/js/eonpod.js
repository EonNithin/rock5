let selectedSubject = '';
let isLanguage = '';
let isConnected = false;
let isRecording = false;
let isLoggingOut = false;

document.addEventListener('DOMContentLoaded', function() {
    const logoutButton = document.getElementById('logout');

    if (logoutButton) {
        logoutButton.addEventListener('click', logoutFunction);
    }

    // Initial check for device connections
    checkDeviceConnections();
});

function logoutFunction() {
    isLoggingOut = true; // Set flag to indicate logout process
    if (isRecording) {
        // If recording is active, stop it first
        stopRecording().then(() => {
            window.location.href = '/login_page/';
        });
    } else {
        // If not recording, proceed to logout
        window.location.href = '/login_page/';
    }
}

window.addEventListener('unload', async function (event) {
    if (isLoggingOut) return; // Skip if logging out
    console.log('Window is closing, sending fetch request...');
    alert("You are leaving the window... Recording will be autosaved");

    // Stop recording if it's active
    if (isRecording) {
        await stopRecording(); // Wait for recording to stop
    }
});

var messageElement = document.getElementById('welcome-message');
console.log(messageElement);

if (messageElement) {
    console.log("Welcome message element found:", messageElement);
    setTimeout(function() {
        console.log("Timeout function triggered");
        messageElement.style.display = 'none';
    }, 5000); // 5000 milliseconds = 5 seconds
}

function updateStatus(data) {
    document.getElementById('mic').setAttribute('fill', data.mic_status ? '#a9dfbf' : '#f8c471');
    document.getElementById('camera').setAttribute('fill', data.camera_status ? '#a9dfbf' : '#f8c471');
    document.getElementById('screen-capture').setAttribute('fill', data.screen_capture_status ? '#a9dfbf' : '#f8c471');
}

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

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function toggleRecording() {
    const startRecordButton = document.getElementById("startRecord");
    const stopRecordButton = document.getElementById("stopRecord");
    const textLabelRecord = document.getElementById("text-label-record");
    const progressBar = document.getElementById("progress-bar1");
    const controlsDiv = document.getElementById('controls');
    const pauseRecordButton = document.getElementById("pause-recording");
    const resumeRecordContainer = document.getElementById("resume-recording");
    const dropdownLabel = document.getElementById("dropdown-label");
    const dropdownContent = document.getElementById("dropdown-content");

    if (isRecording) {
        // Stop recording
        showConfirmDialog();
    } else {
        // Start recording
        if (!selectedSubject) {
            showSubjectSelectionAlert();
            console.log("entered function showSubjectSelectionAlert")
            return;
        }

        startRecordButton.style.display = "none";
        stopRecordButton.style.display = "block";
        textLabelRecord.textContent = "Stop Recording";
        progressBar.style.visibility = "visible"; // Show progress bar
        controlsDiv.style.display = 'block';
        pauseRecordButton.style.display = "block";
        resumeRecordContainer.style.display = "none";

        // Disable dropdown while recording
        dropdownLabel.style.pointerEvents = "none"; // Disable dropdown label
        dropdownContent.style.pointerEvents = "none"; // Disable dropdown options

        isRecording = true;

        try {
            let startRecordingResponse = await fetch('/start_recording_view/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ 
                    subject: selectedSubject,   
                    isLanguage: isLanguage      
                })
            });

            let startRecordingData = await startRecordingResponse.json();
            console.log("start recording view response", startRecordingData.message);
        } catch (error) {
            console.error('Failed to start recording:', error);
        }
    }
}

function toggleDropdown() {
    document.getElementById("dropdown-content").classList.toggle("show");
}

function selectOption(displayValue, title, language) {
    const dropdownLabel = document.getElementById("dropdown-label").children[0];
    if (dropdownLabel) {
        dropdownLabel.textContent = displayValue;
        selectedSubject = title;
        isLanguage = language;
        console.log(`Selected Title is selected subject: ${selectedSubject}`);
        console.log(`Selected Subject is language subject: ${isLanguage}`);
    } else {
        console.error('Dropdown label element not found.');
    }
    document.getElementById("dropdown-content").classList.remove("show");
}

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

function showSettings() {
   console.log("clicked settings icon");
   const settings = document.getElementById('settings');
   settings.style.display = (settings.style.display === 'none' || settings.style.display === '') ? 'block' : 'none';
}

document.addEventListener('click', function(event) {
   const gearIcon = document.getElementById('gear-icon');
   const settings = document.getElementById('settings');
   if (!gearIcon.contains(event.target)) {
       settings.style.display = 'none';
   }
});

function requestFullScreen() {
   const elem = document.documentElement;
   if (elem.requestFullscreen) {
       elem.requestFullscreen();
   } else if (elem.mozRequestFullScreen) {
       elem.mozRequestFullScreen();
   } else if (elem.webkitRequestFullscreen) {
       elem.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
   } else if (elem.msRequestFullscreen) {
       elem.msRequestFullscreen();
   }
}

function exitFullScreen() {
   const elem = document;
   if (elem.exitFullscreen) {
       elem.exitFullscreen();
   } else if (elem.mozCancelFullScreen) {
       elem.mozCancelFullScreen();
   } else if (elem.webkitExitFullscreen) {
       elem.webkitExitFullscreen();
   } else if (elem.msRequestFullscreen) {
       elem.msRequestFullscreen();
   }
}

document.addEventListener("DOMContentLoaded", function() {
   const fullscreenButton = document.getElementById("fullscreenButton");
   const fullscreenExitButton = document.getElementById("fullscreenExitButton");

   if (fullscreenButton) {
       fullscreenButton.addEventListener("click", function() {
           fullscreenButton.style.display = 'none';
           fullscreenExitButton.style.display = 'block';
           requestFullScreen();
       }); 
   }

   if (fullscreenExitButton) {
       fullscreenExitButton.addEventListener("click", function() {
           fullscreenButton.style.display = 'block';
           fullscreenExitButton.style.display = 'none';
           exitFullScreen();
       }); 
   }
});

function showConfirmDialog() {
    const modal = document.getElementById("customConfirm");
    const customAlert = document.getElementById("customAlert");

    modal.style.display = "block";

    document.getElementById("confirmBtn").onclick = async function () {
        modal.style.display = "none"; // Close the confirm modal
        customAlert.style.display = "block"; // Show the custom alert

        setTimeout(async function () {
            customAlert.style.display = "none"; // Hide the custom alert after 5 seconds
            await stopRecording(); // Stop the recording automatically
            logoutFunction(); // Call logout after stopping recording
        }, 5000); // 5000 milliseconds = 5 seconds
    };

    document.getElementById("cancelBtn").onclick = function () {
        modal.style.display = "none"; // Close the modal
        console.log('Recording continues.');
    };
}

async function stopRecording() {
    try {
        const controlsDiv = document.getElementById('controls');
        controlsDiv.style.display = 'none';
        document.getElementById("startRecord").style.display = "block";
        document.getElementById("stopRecord").style.display = "none";
        document.getElementById("text-label-record").textContent = "Start Recording";
        document.getElementById("progress-bar1").style.visibility = "hidden"; // Hide progress bar
        document.getElementById("progress-bar1").style.width = "0%"; // Reset progress bar

        const dropdownLabel = document.getElementById("dropdown-label");
        const dropdownContent = document.getElementById("dropdown-content");

        // Re-enable dropdown after stopping recording
        dropdownLabel.style.pointerEvents = "auto"; // Enable dropdown label
        dropdownContent.style.pointerEvents = "auto"; // Enable dropdown options
        
        const pauseRecordButton = document.getElementById("pause-recording");
        const resumeRecordContainer = document.getElementById("resume-recording");
        pauseRecordButton.style.display = "none";
        resumeRecordContainer.style.display = "none";

        isRecording = false;

        let response = await fetch('/stop_recording_view/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ 
                subject: selectedSubject,   
                isLanguage: isLanguage      
            })
        });

        let data = await response.json();
        console.log(data.message);
    } catch (error) {
        console.error('Failed to stop recording:', error);
    }
}

// Close custom alert when clicking outside of the alert box
window.onclick = function (event) {
    const customAlert = document.getElementById("customAlert");
    if (event.target === customAlert) {
        customAlert.style.display = "none"; // Close the custom alert
    }
};


function showSubjectSelectionAlert(){
    const subjectmodal = document.getElementById('selectSubjectModal');
    const confirmBtn = document.getElementById('selectSubjectConfirmBtn');

    subjectmodal.style.display = 'block';
    
}

// Function to close the modal
function closeSubjectModal() {
    const subjectmodal = document.getElementById('selectSubjectModal');
    subjectmodal.style.display = 'none';
}

// Attach event listener to the "OK" button to close the modal (only once)
document.getElementById('selectSubjectConfirmBtn').addEventListener('click', closeSubjectModal);

// Function to close the modal when clicking outside of it
window.onclick = function(event) {
    const subjectmodal = document.getElementById('selectSubjectModal');

    if (event.target === subjectmodal) {
        subjectmodal.style.display = 'none';
    }
}