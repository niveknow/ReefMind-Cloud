from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.csv_import import CsvImport
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/csv", tags=["csv"])


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    import uuid
    import tempfile, os

    content = await file.read()
    file_size = len(content)

    csv_import = CsvImport(
        tenant_id=tenant_id,
        filename=file.filename or "unknown.csv",
        file_size=file_size,
        status="pending",
    )
    db.add(csv_import)
    await db.commit()
    await db.refresh(csv_import)

    # Parse headers for preview
    import csv, io
    try:
        text = content.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        headers = next(reader, [])
        preview_rows = [row for _, row in zip(range(5), reader)]
    except Exception as e:
        headers = []
        preview_rows = []

    return {
        "import_id": str(csv_import.id),
        "filename": csv_import.filename,
        "file_size": file_size,
        "headers": headers,
        "preview_rows": preview_rows,
        "status": "pending",
    }


@router.get("/imports")
async def list_imports(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(CsvImport)
        .where(CsvImport.tenant_id == tenant_id)
        .order_by(CsvImport.created_at.desc())
        .limit(20)
    )
    imports = result.scalars().all()

    return {
        "imports": [
            {
                "id": str(i.id),
                "filename": i.filename,
                "file_size": i.file_size,
                "rows_imported": i.rows_imported,
                "status": i.status,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in imports
        ]
    }
