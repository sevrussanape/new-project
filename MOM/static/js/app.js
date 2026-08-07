const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const statusContainer = document.getElementById('status-container');
const uploadCardContent = document.querySelector('.drop-zone');
const resultContainer = document.getElementById('result-container');
const errorContainer = document.getElementById('error-container');
const currentStep = document.getElementById('current-step');
const progressFill = document.getElementById('progress-fill');
const progressPercent = document.getElementById('progress-percent');
const downloadBtn = document.getElementById('download-btn');
const resetBtn = document.getElementById('reset-btn');
const retryBtn = document.getElementById('retry-btn');
const errorMessage = document.getElementById('error-message');

let pollInterval;

// File Selection & Drag Events
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length) handleUpload(files[0]);
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) handleUpload(fileInput.files[0]);
});

async function handleUpload(file) {
    // UI Change
    uploadCardContent.classList.add('hidden');
    statusContainer.classList.remove('hidden');
    errorContainer.classList.add('hidden');
    resultContainer.classList.add('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.status === 'started') {
            startPolling();
        } else {
            showError(data.error || 'Upload failed');
        }
    } catch (err) {
        showError('Network error occurred during upload');
    }
}

function startPolling() {
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/status');
            const data = await response.json();

            updateUI(data);

            if (data.status === 'done') {
                clearInterval(pollInterval);
                showResult(data.result_file);
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                showError(data.error);
            }
        } catch (err) {
            console.error('Polling error', err);
        }
    }, 2000);
}

function updateUI(data) {
    currentStep.innerText = data.step;
    progressFill.style.width = `${data.progress}%`;
    progressPercent.innerText = `${data.progress}%`;
}

function showResult(filename) {
    statusContainer.classList.add('hidden');
    resultContainer.classList.remove('hidden');
    downloadBtn.href = `/download/${filename}`;
}

function showError(msg) {
    statusContainer.classList.add('hidden');
    uploadCardContent.classList.add('hidden');
    errorContainer.classList.remove('hidden');
    errorMessage.innerText = msg;
}

resetBtn.addEventListener('click', resetUI);
retryBtn.addEventListener('click', resetUI);

function resetUI() {
    statusContainer.classList.add('hidden');
    resultContainer.classList.add('hidden');
    errorContainer.classList.add('hidden');
    uploadCardContent.classList.remove('hidden');
    fileInput.value = '';
    clearInterval(pollInterval);
}
