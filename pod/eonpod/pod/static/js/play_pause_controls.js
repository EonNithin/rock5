document.getElementById('pause-recording').addEventListener('click', function() {
    console.log('Pause button clicked');
    const pauseRecordButton = document.getElementById("pause-recording");
    const resumeRecordContainer = document.getElementById("resume-recording");
    const pause_resume_textlabel = document.getElementById("text-label");
    const progressBar = document.getElementById("progress-bar1");

    pauseRecordButton.style.display = "none";
    resumeRecordContainer.style.display = "block";
    pause_resume_textlabel.textContent = "Resume Recording";  // Corrected here
    // progressBar.style.visibility = "visible"; // Show progress bar

    // Send POST request to pause recording
    fetch('/pause_recording_view/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()  // Include CSRF token if needed
        }
    })
    .then(response => response.json())
    console.log('Response received from pause recording view');
});

document.getElementById('resume-recording').addEventListener('click', function() {
    console.log('resume button clicked');
    const pauseRecordButton = document.getElementById("pause-recording");
    const resumeRecordContainer = document.getElementById("resume-recording");
    const pause_resume_textlabel = document.getElementById("text-label");
    const progressBar = document.getElementById("progress-bar1");

    pauseRecordButton.style.display = "block";
    resumeRecordContainer.style.display = "none";
    pause_resume_textlabel.textContent = "Pause Recording";  // Corrected here
    // progressBar.style.visibility = "visible"; // Show progress bar

    // Send POST request to resume recording
    fetch('/resume_recording_view/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()  // Include CSRF token if needed
        }
    })
    console.log('Response received from resume recording view');
});


// Helper function to retrieve CSRF token from cookies (if CSRF protection is enabled)
function getCSRFToken() {
    let name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}