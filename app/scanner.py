import re
import os
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple
from app.config import get_library_dir
from app.database import get_db, init_db

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

def extract_pdf_page_count(file_path: Path) -> int:
    if not HAS_PYPDF:
        return 0
    try:
        reader = PdfReader(str(file_path))
        return len(reader.pages)
    except Exception:
        # Fast regex fallback for raw PDF binary
        try:
            with open(file_path, "rb") as f:
                data = f.read(1024 * 512) # read first 512KB
                match = re.search(rb'/Count\s+(\d+)', data)
                if match:
                    return int(match.group(1).decode('ascii'))
        except Exception:
            pass
        return 0

def extract_epub_page_count(file_path: Path) -> int:
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            total_chars = 0
            for name in zf.namelist():
                if name.endswith(('.html', '.xhtml', '.htm')):
                    total_chars += len(zf.read(name))
            # Estimate ~2000 characters per standard printed page
            return max(1, round(total_chars / 2000))
    except Exception:
        return 0

def parse_book_filename(filename: str) -> Tuple[str, str, str]:
    stem = Path(filename).stem
    
    match = re.match(r'^\((\d{4}|XXXX)\)\s*(.*?)\s*-\s*(.*)$', stem)
    if match:
        year = match.group(1)
        raw_title = match.group(2).replace('_', ' ').strip()
        raw_author = match.group(3).replace('_', ' ').strip()
        return raw_title, raw_author, year
        
    match2 = re.match(r'^\((\d{4}|XXXX)\)\s*(.*)$', stem)
    if match2:
        year = match2.group(1)
        raw_title = match2.group(2).replace('_', ' ').strip()
        return raw_title, "Autor Desconhecido", year
        
    if ' - ' in stem:
        parts = stem.split(' - ', 1)
        raw_title = parts[0].replace('_', ' ').strip()
        raw_author = parts[1].replace('_', ' ').strip()
        return raw_title, raw_author, "XXXX"
        
    raw_title = stem.replace('_', ' ').strip()
    return raw_title, "Autor Desconhecido", "XXXX"

def scan_and_sync_library() -> int:
    init_db()
    lib_dir = get_library_dir()
    if not lib_dir or not lib_dir.exists():
        print("Biblioteca não configurada ou diretório inexistente.")
        return 0
        
    print(f"Scanning dynamic library at: {lib_dir}...")
    t0 = time.time()
    
    valid_exts = {'.pdf', '.epub'}
    files_to_sync = []
    
    for root, dirs, files in os.walk(lib_dir):
        rel_root = Path(root).relative_to(lib_dir)
        parts = rel_root.parts
        
        if len(parts) == 0:
            category = "Geral"
            language = "Geral"
        elif len(parts) == 1:
            category = parts[0]
            language = "Geral"
        else:
            category = parts[0]
            language = parts[1]
            
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in valid_exts:
                abs_p = Path(root) / f
                rel_p = str(abs_p.relative_to(lib_dir))
                files_to_sync.append((abs_p, rel_p, category, language, f, ext[1:]))
                
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, rel_path, size_bytes, page_count FROM books")
    existing_map = {row["rel_path"]: (row["id"], row["size_bytes"], row["page_count"]) for row in cursor.fetchall()}
    
    current_rel_paths = set()
    to_insert = []
    to_update = []
    
    for abs_path, rel_path, category, language, filename, fmt in files_to_sync:
        current_rel_paths.add(rel_path)
        title, author, year = parse_book_filename(filename)
        size_bytes = abs_path.stat().st_size
        
        if rel_path in existing_map:
            book_id, old_size, old_pages = existing_map[rel_path]
            # If pages are 0 or file modified, extract pages
            if old_size != size_bytes or not old_pages or old_pages <= 0:
                pages = extract_pdf_page_count(abs_path) if fmt == 'pdf' else extract_epub_page_count(abs_path)
                to_update.append((filename, title, author, year, category, language, fmt, size_bytes, pages, str(abs_path), rel_path, book_id))
        else:
            pages = extract_pdf_page_count(abs_path) if fmt == 'pdf' else extract_epub_page_count(abs_path)
            to_insert.append((filename, title, author, year, category, language, fmt, size_bytes, pages, rel_path, str(abs_path)))
            
    if to_insert:
        cursor.executemany("""
        INSERT INTO books (filename, title, author, year, category, language, format, size_bytes, page_count, rel_path, abs_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, to_insert)
        
    if to_update:
        cursor.executemany("""
        UPDATE books 
        SET filename = ?, title = ?, author = ?, year = ?, category = ?, language = ?, format = ?, size_bytes = ?, page_count = ?, abs_path = ?, rel_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, to_update)
        
    deleted_paths = set(existing_map.keys()) - current_rel_paths
    if deleted_paths:
        cursor.executemany("DELETE FROM books WHERE rel_path = ?", [(p,) for p in deleted_paths])
        
    conn.commit()
    conn.close()
    
    elapsed = time.time() - t0
    total_count = len(files_to_sync)
    print(f"Library sync completed in {elapsed:.2f}s! Total books: {total_count} (+{len(to_insert)} inserted, ~{len(to_update)} updated, -{len(deleted_paths)} deleted).")
    return total_count
