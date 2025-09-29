"""Web interface for Ankicraft - a web-based interface for generating flashcards from PDFs."""
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router
from .settings import WebSettings

app = FastAPI(title="Ankicraft Web Interface")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Settings
web_settings = WebSettings()

@app.get("/")
async def read_root():
    """Serve the main web page."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ankicraft - PDF to Flashcards</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .upload-area {
                border: 2px dashed #ccc;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
                margin: 20px 0;
                cursor: pointer;
                transition: border-color 0.3s;
            }
            .upload-area:hover {
                border-color: #007bff;
            }
            .upload-area.dragover {
                border-color: #007bff;
                background-color: #f0f8ff;
            }
            .file-input {
                display: none;
            }
            .btn {
                background-color: #007bff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px 5px;
            }
            .btn:hover {
                background-color: #0056b3;
            }
            .btn:disabled {
                background-color: #ccc;
                cursor: not-allowed;
            }
            .progress-container {
                margin: 20px 0;
                display: none;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background-color: #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
            }
            .progress-bar-fill {
                height: 100%;
                background-color: #4CAF50;
                width: 0%;
                transition: width 0.3s;
            }
            .status {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
            }
            .status.success {
                background-color: #d4edda;
                color: #155724;
            }
            .status.error {
                background-color: #f8d7da;
                color: #721c24;
            }
            .download-link {
                display: none;
                margin: 20px 0;
                text-align: center;
            }
            .download-link a {
                background-color: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                text-decoration: none;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Ankicraft - Convert PDFs to Flashcards</h1>
            <p>Upload a PDF file to generate Anki flashcards automatically. The system will process your document and create question & answer pairs.</p>
            
            <div class="upload-area" id="uploadArea">
                <p>Drag & drop your PDF file here or click to browse</p>
                <input type="file" id="fileInput" class="file-input" accept=".pdf">
                <button class="btn" onclick="document.getElementById('fileInput').click()">Select PDF File</button>
            </div>
            
            <div style="text-align: center;">
                <button id="processBtn" class="btn" disabled>Process PDF</button>
            </div>
            
            <div class="progress-container" id="progressContainer">
                <div>Processing your file...</div>
                <div class="progress-bar">
                    <div class="progress-bar-fill" id="progressBarFill"></div>
                </div>
                <div id="progressText">0%</div>
            </div>
            
            <div class="status" id="statusMessage"></div>
            
            <div class="download-link" id="downloadLink">
                <a href="#" id="downloadAnchor">Download Generated Flashcards</a>
            </div>
        </div>

        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const processBtn = document.getElementById('processBtn');
            const progressContainer = document.getElementById('progressContainer');
            const progressBarFill = document.getElementById('progressBarFill');
            const progressText = document.getElementById('progressText');
            const statusMessage = document.getElementById('statusMessage');
            const downloadLink = document.getElementById('downloadLink');
            const downloadAnchor = document.getElementById('downloadAnchor');
            
            let selectedFile = null;
            
            // Handle file selection
            fileInput.addEventListener('change', function(e) {
                if (e.target.files.length > 0) {
                    selectedFile = e.target.files[0];
                    processBtn.disabled = false;
                    uploadArea.querySelector('p').textContent = selectedFile.name;
                    statusMessage.textContent = '';
                    statusMessage.className = 'status';
                }
            });
            
            // Drag and drop functionality
            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            
            uploadArea.addEventListener('dragleave', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });
            
            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                
                if (e.dataTransfer.files.length > 0) {
                    const file = e.dataTransfer.files[0];
                    if (file.type === 'application/pdf') {
                        selectedFile = file;
                        fileInput.files = e.dataTransfer.files;
                        processBtn.disabled = false;
                        uploadArea.querySelector('p').textContent = file.name;
                        statusMessage.textContent = '';
                        statusMessage.className = 'status';
                    } else {
                        statusMessage.textContent = 'Please upload a PDF file only';
                        statusMessage.className = 'status error';
                    }
                }
            });
            
            // Process the file when button is clicked
            processBtn.addEventListener('click', async function() {
                if (!selectedFile) return;
                
                const formData = new FormData();
                formData.append('file', selectedFile);
                
                // Show progress
                progressContainer.style.display = 'block';
                downloadLink.style.display = 'none';
                
                try {
                    // Upload and start processing
                    const uploadResponse = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!uploadResponse.ok) {
                        throw new Error('Upload failed');
                    }
                    
                    const uploadData = await uploadResponse.json();
                    const fileId = uploadData.file_id;
                    
                    // Poll for progress
                    let status = 'processing';
                    while (status === 'processing' || status === 'started') {
                        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
                        
                        const statusResponse = await fetch(`/api/status/${fileId}`);
                        const statusData = await statusResponse.json();
                        
                        status = statusData.status;
                        const progress = statusData.progress || 0;
                        
                        // Update progress bar
                        progressBarFill.style.width = progress + '%';
                        progressText.textContent = Math.round(progress) + '%';
                        
                        // Update status message
                        statusMessage.textContent = statusData.status || 'Processing...';
                        statusMessage.className = 'status';
                        
                        if (status === 'completed') {
                            statusMessage.textContent = 'Processing completed successfully!';
                            statusMessage.className = 'status success';
                            
                            // Show download link
                            downloadLink.style.display = 'block';
                            downloadAnchor.href = `/api/download/${fileId}`;
                            downloadAnchor.textContent = `Download ${statusData.filename || 'flashcards.apkg'}`;
                            break;
                        } else if (status === 'error') {
                            statusMessage.textContent = statusData.error || 'An error occurred during processing';
                            statusMessage.className = 'status error';
                            break;
                        }
                    }
                } catch (error) {
                    statusMessage.textContent = 'Error: ' + error.message;
                    statusMessage.className = 'status error';
                    progressContainer.style.display = 'none';
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)