import re
import os
import time
from pathlib import Path
from typing import Tuple
from app.config import get_library_dir
from app.database import get_db, init_db

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
        
    print(f"Sincronizando acervo em: {lib_dir}...")
    t0 = time.time()
    
    valid_exts = {'.pdf', '.epub'}
    files_to_sync = []
    
    # Fast os.walk (does not open binary contents over Google Drive network stream)
    for root, dirs, files in os.walk(lib_dir):
        try:
            rel_root = Path(root).relative_to(lib_dir)
            parts = rel_root.parts
        except ValueError:
            parts = ()
        
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
                try:
                    rel_p = str(abs_p.relative_to(lib_dir))
                except ValueError:
                    rel_p = f
                files_to_sync.append((abs_p, rel_p, category, language, f, ext[1:]))
                
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, rel_path, size_bytes FROM books")
    existing_map = {row["rel_path"]: (row["id"], row["size_bytes"]) for row in cursor.fetchall()}
    
    current_rel_paths = set()
    to_insert = []
    to_update = []
    
    for abs_path, rel_path, category, language, filename, fmt in files_to_sync:
        current_rel_paths.add(rel_path)
        title, author, year = parse_book_filename(filename)
        try:
            size_bytes = abs_path.stat().st_size
        except Exception:
            size_bytes = 0
            
        if rel_path in existing_map:
            book_id, old_size = existing_map[rel_path]
            if old_size != size_bytes:
                to_update.append((filename, title, author, year, category, language, fmt, size_bytes, str(abs_path), rel_path, book_id))
        else:
            to_insert.append((filename, title, author, year, category, language, fmt, size_bytes, 0, rel_path, str(abs_path)))
            
    if to_insert:
        cursor.executemany("""
        INSERT INTO books (filename, title, author, year, category, language, format, size_bytes, page_count, rel_path, abs_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, to_insert)
        
    if to_update:
        cursor.executemany("""
        UPDATE books 
        SET filename = ?, title = ?, author = ?, year = ?, category = ?, language = ?, format = ?, size_bytes = ?, abs_path = ?, rel_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, to_update)
        
    deleted_paths = set(existing_map.keys()) - current_rel_paths
    if deleted_paths:
        cursor.executemany("DELETE FROM books WHERE rel_path = ?", [(p,) for p in deleted_paths])
        
    conn.commit()
    conn.close()
    
    elapsed = time.time() - t0
    total_count = len(files_to_sync)
    print(f"Sincronização concluída com sucesso em {elapsed:.2f}s! Total de livros: {total_count:,} (+{len(to_insert):,} novos, ~{len(to_update):,} atualizados, -{len(deleted_paths):,} removidos).")
    return total_count
