
function showConfirmDialog() {
    // const controlsDiv = document.getElementById('controls');
    const modal = document.getElementById("customConfirm");
    const startRecordButton = document.getElementById("startRecord");
    const stopRecordButton = document.getElementById("stopRecord");
    const textLabelRecord = document.getElementById("text-label-record");
    const progressBar = document.getElementById("progress-bar1");
    const customAlert = document.getElementById("customAlert");
    const pauseRecordButton = document.getElementById("pause-recording");
    const resumeRecordContainer = document.getElementById("resume-recording");

    // Show the confirm modal
    modal.style.display = "block";

    // Handle confirm (OK)
    document.getElementById("confirmBtn").onclick = async function () {
        modal.style.display = "none"; // Close the confirm modal
        customAlert.style.display = "block"; // Show the custom alert

        // Automatically stop recording after 10 seconds and hide the custom alert
        setTimeout(async function () {
            customAlert.style.display = "none"; // Hide the custom alert after 10 seconds
            await stopRecording(); // Stop the recording automatically
        }, 5000); // 10,000 milliseconds = 10 seconds
    };

    // Handle cancel
    document.getElementById("cancelBtn").onclick = function () {
        modal.style.display = "none"; // Close the modal
        console.log('Recording continues.');
    };
}

// Function to stop the recording
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

        // Show pause button, hide resume button initially
        pauseRecordButton.style.display = "none";
        resumeRecordContainer.style.display = "none";

        isRecording = false;

        document.getElementById('pause-svg').setAttribute('fill', 'black');
        console.log("Pause svg color changed to black");
        document.getElementById('resume-svg').setAttribute('fill', 'black');
        console.log("Resume svg color changes to black");

        let response = await fetch('/stop_recording_view/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ 
                subject: selectedSubject,   // Send selectedSubject 
                isLanguage: isLanguage      // Send isLanguage
            })
        });

        let data = await response.json();

        console.log(data.message);
        
        // checkDeviceConnections();
        // Programmatically trigger the click event
        console.log("Logging out");
        document.getElementById('logout').click();

    } catch (error) {
        console.error('Failed to stop recording:', error);
    }
}

// Close custom alert when clicking outside of the alert box
window.onclick = function (event) {
    const customAlert = document.getElementById("customAlert");

    // Close the custom alert if the user clicks outside of it
    if (event.target === customAlert) {
        customAlert.style.display = "none"; // Close the custom alert
    }
};
