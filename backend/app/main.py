import os
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Task
from app.models import Upload, Output
from app.npi_service import call_npi_api
from app.excel_service import write_to_excel
from app.utils.file_reader import read_excel_file

import time
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "storage/uploads"
OUTPUT_DIR = "storage/outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# BACKGROUND PROCESSOR 
def process_file_background(task_id: str, input_path: str, output_path: str):
    db = SessionLocal()

    try:
        rows = read_excel_file(input_path)
        results = []
        

        # ---- DELAY----
        DELAY_SECONDS = 0.15     

        lock = threading.Lock()
        last_call_time = [0]

         # ---- PROCESSING ----
        if len(rows) <= 100:
            for row in rows:
                results.extend(call_npi_api(row))
        else:
            workers = min(4, len(rows))
            def delayed_call(row):
                with lock:
                    now = time.time()
                    elapsed = now - last_call_time[0]

                    if elapsed < DELAY_SECONDS:
                        time.sleep(DELAY_SECONDS - elapsed)

                    last_call_time[0] = time.time()

                return call_npi_api(row)

            with ThreadPoolExecutor(max_workers=workers) as executor:
                for data in executor.map(delayed_call, rows):
                    results.extend(data)

        # ---- WRITE EXCEL ----
        write_to_excel(results, output_path)

        total_processed = len(results)
        total_failed = sum(1 for r in results if r.get("Status") == "Failed")

        # ---- FETCH TASK ----
        task = db.query(Task).filter(Task.id == UUID(task_id)).first()

        if task:
            # Insert output record
            output_record = Output(
                task_id=task.id,
                stored_path=output_path,
                total_processed=total_processed,
                total_failed=total_failed
            )
            db.add(output_record)

            filename = os.path.basename(output_path)

            # Update task
            task.status = "completed"
            task.output_file = filename
            task.completed_at = datetime.now(timezone.utc)

            db.commit()

    except Exception as e:
        print("Background error:", e)

    finally:
        db.close()

# Upload Endpoint
@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files allowed")

    original_name = os.path.splitext(file.filename)[0]
    short_id = uuid.uuid4().hex[:6]
    unique_name = f"{original_name}_{short_id}.xlsx"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    db: Session = SessionLocal()

    try:

        # Count rows
        rows = read_excel_file(file_path)
        total_rows = len(rows)

        # INSERT INTO uploads
        upload_record = Upload(
            original_filename=file.filename,
            stored_path=file_path,
            total_rows=total_rows
        )

        db.add(upload_record)
        db.commit()
        db.refresh(upload_record)

        task = Task(
            status="processing",
            input_file=file_path,
            upload_id=upload_record.id
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        task_id = str(task.id)

    finally:
        db.close()

    output_filename = f"{original_name}_{short_id}.xlsx"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    background_tasks.add_task(
        process_file_background,
        str(task.id),
        file_path,
        output_path
    )

    return {
        "task_id": str(task.id),
        "message": "File uploaded. Processing started."
    }


# Status Endpoint
@app.get("/status/{task_id}")
def check_status(task_id: str):

    db = SessionLocal()

    try:
        task_uuid = UUID(task_id)   

        task = db.query(Task).filter(Task.id == task_uuid).first()

        if not task:
            return {"error": "Task not found"}

        return {
            "task_id": task_id,
            "status": task.status,
            "output_file": task.output_file
        }

    finally:
        db.close()


@app.get("/download/{filename}")
def download_file(filename: str):

    file_path = os.path.join(OUTPUT_DIR, filename)

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )