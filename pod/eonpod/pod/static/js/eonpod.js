let isConnected = false;
let isRecording = false;
let isLoggingOut = false;

// Global variable to store subjectdata and subjectgroups
let subjectdata = {};

// On DOMContentLoaded, retrieve subjectdata and subjectgroups from sessionStorage
document.addEventListener('DOMContentLoaded', () => {
    // Retrieve and parse subjectdata
    const storedData = sessionStorage.getItem('subjectdata');
    if (storedData) {
        subjectdata = JSON.parse(storedData);
        console.log('Retrieved Subject Data from sessionStorage:', subjectdata);
    } else {
        console.error('No subject data found in sessionStorage');
    }

});

// Get modal and elements
const backWarningModal = document.getElementById("backWarningModal");
const closeBackWarningModalBtn = document.getElementById("closeBackWarningModal");
const backButton = document.getElementById("backButton");

// Function to show the modal
function showBackWarningModal() {
    backWarningModal.style.display = "block";
}

// Function to close the modal
function closeBackWarningModal() {
    backWarningModal.style.display = "none";
}

// Event listener for the back button
backButton.addEventListener("click", function(event) {
    if (isRecording) {
        event.preventDefault(); // Prevent the redirect
        showBackWarningModal(); // Show warning modal
    } else {
        // Redirect to the desired page if no recording is in progress
        window.location.href = "/subjectcards/";
    }
});

// Add event listener for the OK button in the modal
document.getElementById('backWarningModal-confirmBtn').addEventListener('click', function() {
    // Close the modal
    document.getElementById('backWarningModal').style.display = 'none';
});

// Close modal when clicking outside of it
window.onclick = function(event) {
    if (event.target === backWarningModal) {
        closeBackWarningModal(); // Call the function to close the modal
    }
}


document.addEventListener('DOMContentLoaded', function() {
    const logoutButton = document.getElementById('logout');
    const refreshButton = document.getElementById('refreshButton'); // Select refresh button
    if (logoutButton) {
        logoutButton.addEventListener('click', logoutFunction);
    }

    if (refreshButton) {
        refreshButton.addEventListener('click', checkDeviceConnections); // Call checkDeviceConnections on click
    }

    // Initial check for device connections
    checkDeviceConnections();
});

// function logoutFunction() {
//     isLoggingOut = true; // Set flag to indicate logout process
//     if (isRecording) {
//         // If recording is active, stop it first
//         stopRecording().then(() => {
//             window.location.href = '/login_page/';
//         });
//     } else {
//         // If not recording, proceed to logout
//         window.location.href = '/login_page/';
//     }
// }

// Logout function with modal confirmation
function logoutFunction() {
    isLoggingOut = true; // Set flag to indicate logout process
    if (isRecording) {
        // If recording is active, prevent logout and show warning modal
        showBackWarningModal();
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


function updateStatus(data) {
    document.getElementById('mic').setAttribute('fill', data.mic_status ? 'green' : 'red');
    document.getElementById('camera').setAttribute('fill', data.camera_status ? 'green' : 'red');
    document.getElementById('screen-capture').setAttribute('fill', data.screen_capture_status ? 'green' : 'red');
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

    if (isRecording) {
        // Stop recording
        showConfirmDialog();
    } else {
        // Start recording
       
        startRecordButton.style.display = "none";
        stopRecordButton.style.display = "block";
        textLabelRecord.textContent = "Stop Capture";
        progressBar.style.visibility = "visible"; // Show progress bar
        controlsDiv.style.display = 'block';
        pauseRecordButton.style.display = "block";
        resumeRecordContainer.style.display = "none";

        isRecording = true;

        try {
            let startRecordingResponse = await fetch('/start_recording_view/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ 
                    subject: subjectdata.title,
                    isLanguage: subjectdata.is_language // Convert string to boolean
                })
            });

            let startRecordingData = await startRecordingResponse.json();
            console.log("start recording view response", startRecordingData.message);
        } catch (error) {
            console.error('Failed to start recording:', error);
        }
    }
}


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
                    subject: subjectdata.title,
                    isLanguage: subjectdata.is_language // Convert string to boolean
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

