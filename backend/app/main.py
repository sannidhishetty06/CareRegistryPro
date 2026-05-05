import os
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID
import time
import threading

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Task, Upload, Output
from app.npi_service import call_npi_api
from app.excel_service import write_to_excel
from app.utils.file_reader import read_excel_file
from app.enrichment_service import enrich_no_match_rows

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "storage/uploads"
OUTPUT_DIR = "storage/outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def process_file_background(task_id: str, input_path: str, output_path: str, batch_id: str):
    """Background task to process uploaded file - SIMPLIFIED"""
    db = SessionLocal()

    try:
        rows = read_excel_file(input_path)
        results = []

        # Rate limiting for API calls
        DELAY_SECONDS = 0.15
        lock = threading.Lock()
        last_call_time = [0]

        # ---- STAGE 1: NPI API LOOKUP ----
        if len(rows) <= 100:
            # Sequential processing for small batches
            for row in rows:
                with lock:
                    now = time.time()
                    elapsed = now - last_call_time[0]
                    if elapsed < DELAY_SECONDS:
                        time.sleep(DELAY_SECONDS - elapsed)
                    last_call_time[0] = time.time()

                try:
                    api_results = call_npi_api(row)
                    results.extend(api_results if api_results else [])
                except Exception as e:
                    print(f"Error processing row: {str(e)}")
                    results.append({
                        "First_Name": row.get("First_Name"),
                        "Last_Name": row.get("Last_Name"),
                        "State": row.get("State"),
                        "Status": "Failed"
                    })

        else:
            # Threaded processing for larger batches
            workers = min(4, len(rows))

            def delayed_call(row):
                with lock:
                    now = time.time()
                    elapsed = now - last_call_time[0]
                    if elapsed < DELAY_SECONDS:
                        time.sleep(DELAY_SECONDS - elapsed)
                    last_call_time[0] = time.time()

                try:
                    return call_npi_api(row)
                except Exception as e:
                    print(f"Error in delayed_call: {str(e)}")
                    return [{
                        "First_Name": row.get("First_Name"),
                        "Last_Name": row.get("Last_Name"),
                        "State": row.get("State"),
                        "Status": "Failed"
                    }]

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(delayed_call, row) for row in rows]
                for future in as_completed(futures):
                    try:
                        data = future.result()
                        results.extend(data if data else [])
                    except Exception as e:
                        print(f"Future error: {str(e)}")

        # ---- STAGE 2: LLM ENRICHMENT FOR NO MATCH ----
        final_results = enrich_no_match_rows(results)

    

        # In process_file_background function, add this AFTER calling enrich_no_match_rows:

        # ---- EXTERNAL ENRICHMENT FOR NO MATCH ----
        print("\n" + "="*60)
        print("STARTING LLM ENRICHMENT")
        print("="*60)
        
        final_results = enrich_no_match_rows(results)
        
        print("\n" + "="*60)
        print("ENRICHMENT COMPLETE")
        print("="*60)
        
        # DEBUG: Check enrichment worked
        no_match_count = sum(1 for r in final_results if r.get("Status") == "No Match")
        llm_suggestion_count = sum(1 for r in final_results if r.get("Status") == "LLM Suggestion")
        success_count = sum(1 for r in final_results if r.get("Status") == "Success")
        failed_count = sum(1 for r in final_results if r.get("Status") == "Failed")
        
        print(f"\nFinal Results Summary:")
        print(f"  Success: {success_count}")
        print(f"  LLM Suggestions: {llm_suggestion_count}")
        print(f"  No Match: {no_match_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Total: {len(final_results)}\n")

        
        # ---- SAVE TO DATABASE ----
        batch_uuid = UUID(batch_id)
        filename = os.path.basename(output_path)

        for r in final_results:
            try:
                db.add(
                    Output(
                        id=batch_uuid,
                        output_file=filename,
                        first_name=r.get("First_Name", ""),
                        last_name=r.get("Last_Name", ""),
                        state=r.get("State", ""),
                        found_first_name=r.get("Found_First_Name"),
                        found_last_name=r.get("Found_Last_Name"),
                        found_state=r.get("Found_State"),
                        full_name=r.get("Full_Name"),
                        npi=r.get("NPI"),
                        mailing_address=r.get("Mailing_Address"),
                        primary_practice_address=r.get("Primary_Practice_Address"),
                        secondary_practice_address=r.get("Secondary_Practice_Address"),
                        taxonomy=r.get("Taxonomy"),
                        specialty=r.get("Specialty"),
                        license=r.get("License"),
                        status=r.get("Status", "Unknown"),
                        ai_confidence=r.get("AI_Confidence")
                    )
                )
            except Exception as e:
                print(f"Database insert error: {str(e)}")

        db.commit()

        # ---- WRITE EXCEL ----
        try:
            write_to_excel(final_results, output_path)
        except Exception as e:
            print(f"Excel write error: {str(e)}")

        # ---- UPDATE TASK STATUS ----
        task = db.query(Task).filter(Task.id == UUID(task_id)).first()
        if task:
            task.status = "completed"
            task.output_file = filename
            task.completed_at = datetime.now(timezone.utc)
            db.commit()

    except Exception as e:
        print(f"Background processing error: {str(e)}")
        db.rollback()
        try:
            task = db.query(Task).filter(Task.id == UUID(task_id)).first()
            if task:
                task.status = "failed"
                task.completed_at = datetime.now(timezone.utc)
                db.commit()
        except:
            pass

    finally:
        db.close()

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Handle file upload and start background processing"""
    
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files allowed")

    original_name = os.path.splitext(file.filename)[0]
    short_id = uuid.uuid4().hex[:6]
    unique_name = f"{original_name}_{short_id}.xlsx"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty file")
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

    db: Session = SessionLocal()

    try:
        # Parse and validate Excel
        try:
            rows = read_excel_file(file_path)
            if not rows:
                raise HTTPException(status_code=400, detail="No valid rows in Excel file")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Excel parse error: {str(e)}")

        batch_id = uuid.uuid4()

        # Store upload metadata
        for r in rows:
            db.add(
                Upload(
                    id=batch_id,
                    original_filename=file.filename,
                    first_name=r.get("First_Name", ""),
                    last_name=r.get("Last_Name", ""),
                    state=r.get("State", "")
                )
            )

        db.commit()

        # Create task record
        task = Task(
            status="processing",
            input_file=file_path,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        task_id = str(task.id)

    except HTTPException:
        db.close()
        raise
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if db:
            db.close()

    # Schedule background processing
    output_filename = f"{original_name}_{short_id}_results.xlsx"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    background_tasks.add_task(
        process_file_background,
        task_id,
        file_path,
        output_path,
        str(batch_id)
    )

    return {
        "task_id": task_id,
        "message": "File uploaded. Processing started.",
        "batch_id": str(batch_id)
    }


@app.get("/status/{task_id}")
def check_status(task_id: str):
    """Check processing status of a task"""
    
    db = SessionLocal()

    try:
        task_uuid = UUID(task_id)
        task = db.query(Task).filter(Task.id == task_uuid).first()

        if not task:
            return {"error": "Task not found", "status": None}

        return {
            "task_id": task_id,
            "status": task.status,
            "output_file": task.output_file,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }

    except ValueError:
        return {"error": "Invalid task ID format"}
    finally:
        db.close()


@app.get("/download/{filename}")
def download_file(filename: str):
    """Download processed results file"""
    
    # Security: validate filename
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}