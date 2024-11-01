let selectedSubject = '';
let subjectdata = {};
let subjectgroups = {}; // Initialize as an array


function selectOption(displayValue, title, active, language) {
    // Update selected subject details
    selectedSubject = displayValue;

    // Log selected subject info (optional)
    console.log(`Selected Subject: ${selectedSubject}, Title: ${title}, Active: ${active}, Is Language: ${language}`);

    // Prepare data to send
    const subjectdata = {
        subject: selectedSubject,
        title: title,
        active: active,
        is_language: language
    };

    // Store `subjectdata` and `subjectgroups` in sessionStorage
    sessionStorage.setItem('subjectdata', JSON.stringify(subjectdata));

    try{
        if(subjectdata){
            window.location.href = '/eonpod/';
        }
        else{
            window.location.href = '/subjectcards/';
        }
    }
    catch (error) {
        console.error('error:', error);
        window.location.href = '/subjectcards/';
    }
}


// Function to get CSRF token (for Django security)
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
