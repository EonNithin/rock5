
document.getElementById('pause-recording').addEventListener('click', function() {
    console.log('Pause button clicked');
    
    // Set fill color for pause SVG and reset resume SVG
    document.getElementById('pause-svg').setAttribute('fill', 'blue');
    console.log("pause svg fill color changed to blue");
    document.getElementById('resume-svg').setAttribute('fill', 'black');
    console.log("resume svg fill color changed to black");

    // Send POST request to pause recording
    fetch('/pause_recording_view/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()  // Include CSRF token if needed
        }
    })
    .then(response => response.json())
    // Add functionality to pause the recording here
    console.log('Response received from pause recording view');
});

document.getElementById('resume-recording').addEventListener('click', function() {
    console.log('resume button clicked');

    // Set fill color for resume SVG and reset pause SVG
    document.getElementById('resume-svg').setAttribute('fill', 'blue');
    console.log("resume svg fill color changed to blue");
    document.getElementById('pause-svg').setAttribute('fill', 'black');
    console.log("pause svg fill color changed to black");

    // Send POST request to resume recording
    fetch('/resume_recording_view/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()  // Include CSRF token if needed
        }
    })

    // Add functionality to resume the recording here
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