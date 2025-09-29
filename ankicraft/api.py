"""API endpoints for Ankicraft."""
import os
import uuid
import asyncio
from typing import Dict
from pathlib import Path
import tempfile

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from .flashcard_generator.processor import process_file
from .settings import FlashcardSettings

router = APIRouter()

# Settings
flashcard_settings = FlashcardSettings()

# Store processing status
processing_status: Dict[str, dict] = {}

class ProcessingStatus:
    def __init__(self, file_id: str, filename: str):
        self.file_id = file_id
        self.filename = filename
        self.status = "started"
        self.progress = 0
        self.result_path = None
        self.error = None

@router.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a PDF file for processing."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create a unique file ID
    file_id = str(uuid.uuid4())
    
    # Create temp directory for this file
    temp_dir = os.path.join(tempfile.gettempdir(), "ankicraft", file_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Save uploaded file
    file_path = os.path.join(temp_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Initialize processing status
    processing_status[file_id] = ProcessingStatus(file_id, file.filename)
    
    # Start background processing task
    background_tasks.add_task(process_pdf_background, file_id, file_path)
    
    return {"file_id": file_id, "filename": file.filename}


@router.get("/status/{file_id}")
async def get_status(file_id: str):
    """Get the processing status for a file."""
    if file_id not in processing_status:
        raise HTTPException(status_code=404, detail="File ID not found")
    
    status = processing_status[file_id]
    return {
        "file_id": status.file_id,
        "filename": status.filename,
        "status": status.status,
        "progress": status.progress,
        "result_path": status.result_path,
        "error": status.error
    }


@router.get("/download/{file_id}")
async def download_file(file_id: str):
    """Download the processed file."""
    if file_id not in processing_status:
        raise HTTPException(status_code=404, detail="File ID not found")
    
    status_obj = processing_status[file_id]
    if status_obj.status != "completed" or not status_obj.result_path:
        raise HTTPException(status_code=400, detail="File not ready for download")
    
    if not os.path.exists(status_obj.result_path):
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        path=status_obj.result_path,
        filename=os.path.basename(status_obj.result_path),
        media_type="application/octet-stream"
    )


async def process_pdf_background(file_id: str, file_path: str):
    """Background task to process the PDF file."""
    status = processing_status[file_id]
    
    try:
        # Update status to processing
        status.status = "processing"
        status.progress = 10  # Start processing
        
        # Process the file to generate flashcards
        result_path = process_file(
            file_path=file_path,
            user_prompt=None,
            deck_name=flashcard_settings.DEFAULT_DECK_NAME,
            coverage_level="maximum"
        )
        
        # Update status to completed
        status.status = "completed"
        status.progress = 100
        status.result_path = result_path
        
    except Exception as e:
        status.status = "error"
        status.progress = 0
        status.error = str(e)