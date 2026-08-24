import os
import base64
import mimetypes
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_config, set_library_dir, get_library_dir, is_library_configured
from app.database import (
    init_db, get_books, get_book_by_id, update_book_metadata,
    move_book, update_reading_progress,
    reset_reading_progress, toggle_favorite, get_stats,
    get_categories_with_counts, get_languages
)
from app.scanner import scan_and_sync_library

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Biblioteca Digital & Leitor Web", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConfigUpdateRequest(BaseModel):
    library_path: str

class MetadataUpdateRequest(BaseModel):
    title: str
    author: str
    year: Optional[str] = "XXXX"

class MoveBookRequest(BaseModel):
    category: str
    language: str

class ReadingProgressRequest(BaseModel):
    current_page: int
    total_pages: Optional[int] = None
    epub_cfi: Optional[str] = None

@app.on_event("startup")
def startup_event():
    init_db()
    lib_dir = get_library_dir()
    if lib_dir and lib_dir.exists():
        stats = get_stats()
        if stats['total_books'] == 0:
            print(f"Initial sync for library at {lib_dir}...")
            scan_and_sync_library()

@app.get("/api/config")
def api_get_config():
    config = get_config()
    lib_dir = get_library_dir()
    exists = lib_dir is not None and lib_dir.exists()
    stats = get_stats() if exists else {"total_books": 0}
    return {
        "library_path": config.get("library_path", ""),
        "exists": exists,
        "total_books": stats["total_books"]
    }

@app.post("/api/config")
def api_set_config(req: ConfigUpdateRequest):
    success, result = set_library_dir(req.library_path)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    
    # Rescan library at new location
    count = scan_and_sync_library()
    return {
        "status": "success",
        "library_path": result,
        "total_synced": count
    }

@app.get("/api/stats")
def api_get_stats():
    return get_stats()

@app.get("/api/categories")
def api_get_categories():
    return get_categories_with_counts()

@app.get("/api/languages")
def api_get_languages():
    return get_languages()

@app.get("/api/books")
def api_get_books(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query("all", description="Category filter"),
    language: Optional[str] = Query("all", description="Language filter"),
    format_type: Optional[str] = Query("all", description="Format filter (pdf, epub)"),
    status: Optional[str] = Query("all", description="Status (unread, reading, completed)"),
    favorite: Optional[bool] = Query(None, description="Favorite filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    sort_by: str = Query("title"),
    sort_order: str = Query("asc")
):
    return get_books(
        query=q,
        category=category,
        language=language,
        format_type=format_type,
        status=status,
        is_favorite=favorite,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

@app.get("/api/books/{book_id}")
def api_get_book(book_id: int):
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return book

@app.post("/api/books/{book_id}/payload")
def api_get_book_payload(book_id: int):
    book = get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    file_path = Path(book['abs_path'])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo físico não encontrado: {book['filename']}")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    b64_data = base64.b64encode(file_bytes).decode("ascii")
    return {
        "status": "success",
        "id": book['id'],
        "title": book['title'],
        "author": book['author'],
        "format": book['format'],
        "filename": book['filename'],
        "size_bytes": len(file_bytes),
        "data": b64_data
    }

@app.put("/api/books/{book_id}/metadata")
def api_update_metadata(book_id: int, req: MetadataUpdateRequest):
    updated_book, err = update_book_metadata(book_id, req.title, req.author, req.year)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return updated_book

@app.put("/api/books/{book_id}/move")
def api_move_book(book_id: int, req: MoveBookRequest):
    updated_book, err = move_book(book_id, req.category, req.language)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return updated_book

@app.put("/api/books/{book_id}/progress")
def api_update_progress(book_id: int, req: ReadingProgressRequest):
    updated_book = update_reading_progress(
        book_id=book_id,
        current_page=req.current_page,
        total_pages=req.total_pages,
        epub_cfi=req.epub_cfi
    )
    if not updated_book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return updated_book

@app.post("/api/books/{book_id}/favorite")
def api_toggle_favorite(book_id: int):
    updated_book = toggle_favorite(book_id)
    if not updated_book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return updated_book

@app.post("/api/sync")
def api_sync_library():
    count = scan_and_sync_library()
    return {"status": "success", "total_synced": count}

@app.post("/api/books/{book_id}/reset-progress")
def reset_progress(book_id: int):
    book = reset_reading_progress(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return {"success": True, "book": book}

# Mount static files
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
