import sqlite3
import re
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.config import get_library_dir

DB_PATH = Path(r"d:\IA\projects\books\library.db")

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year TEXT NOT NULL,
        category TEXT NOT NULL,
        language TEXT NOT NULL,
        format TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        page_count INTEGER DEFAULT 0,
        rel_path TEXT NOT NULL UNIQUE,
        abs_path TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Try adding page_count if table already existed without it
    try:
        cursor.execute("ALTER TABLE books ADD COLUMN page_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reading_progress (
        book_id INTEGER PRIMARY KEY,
        current_page INTEGER DEFAULT 1,
        total_pages INTEGER DEFAULT 1,
        progress_percent REAL DEFAULT 0.0,
        epub_cfi TEXT,
        last_read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_favorite INTEGER DEFAULT 0,
        status TEXT DEFAULT 'unread',
        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_language ON books(language);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_format ON books(format);")
    
    conn.commit()
    conn.close()

def get_books(
    query: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    format_type: Optional[str] = None,
    status: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    page: int = 1,
    page_size: int = 24,
    sort_by: str = "title",
    sort_order: str = "asc"
) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    
    where_clauses = ["1=1"]
    params = []
    
    if query and query.strip():
        q = f"%{query.strip()}%"
        where_clauses.append("(b.title LIKE ? OR b.author LIKE ? OR b.filename LIKE ? OR b.year LIKE ? OR b.category LIKE ?)")
        params.extend([q, q, q, q, q])
        
    if category and category != "all":
        where_clauses.append("b.category = ?")
        params.append(category)
        
    if language and language != "all":
        where_clauses.append("b.language = ?")
        params.append(language)
        
    if format_type and format_type != "all":
        where_clauses.append("b.format = ?")
        params.append(format_type.lower())
        
    if status and status != "all":
        where_clauses.append("COALESCE(rp.status, 'unread') = ?")
        params.append(status)
        
    if is_favorite is not None:
        where_clauses.append("COALESCE(rp.is_favorite, 0) = ?")
        params.append(1 if is_favorite else 0)
        
    where_sql = " AND ".join(where_clauses)
    
    # Count total
    count_sql = f"""
    SELECT COUNT(*) as total 
    FROM books b
    LEFT JOIN reading_progress rp ON b.id = rp.book_id
    WHERE {where_sql}
    """
    cursor.execute(count_sql, params)
    total_count = cursor.fetchone()["total"]
    
    # Allowed sort columns
    sort_mapping = {
        "title": "b.title",
        "author": "b.author",
        "year": "b.year",
        "category": "b.category",
        "pages": "b.page_count",
        "last_read": "rp.last_read_at",
        "progress": "rp.progress_percent"
    }
    order_col = sort_mapping.get(sort_by, "b.title")
    order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"
    
    offset = (page - 1) * page_size
    query_sql = f"""
    SELECT 
        b.id, b.filename, b.title, b.author, b.year, b.category, b.language,
        b.format, b.size_bytes, b.page_count, b.rel_path, b.abs_path, b.created_at, b.updated_at,
        COALESCE(rp.current_page, 1) as current_page,
        CASE WHEN rp.total_pages > 1 THEN rp.total_pages ELSE COALESCE(NULLIF(b.page_count, 0), 1) END as total_pages,
        COALESCE(rp.progress_percent, 0.0) as progress_percent,
        rp.epub_cfi,
        rp.last_read_at,
        COALESCE(rp.is_favorite, 0) as is_favorite,
        COALESCE(rp.status, 'unread') as status
    FROM books b
    LEFT JOIN reading_progress rp ON b.id = rp.book_id
    WHERE {where_sql}
    ORDER BY {order_col} {order_dir}, b.id ASC
    LIMIT ? OFFSET ?
    """
    params.extend([page_size, offset])
    
    cursor.execute(query_sql, params)
    rows = cursor.fetchall()
    
    books = [dict(row) for row in rows]
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    
    conn.close()
    return {
        "items": books,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        b.id, b.filename, b.title, b.author, b.year, b.category, b.language,
        b.format, b.size_bytes, b.page_count, b.rel_path, b.abs_path, b.created_at, b.updated_at,
        COALESCE(rp.current_page, 1) as current_page,
        CASE WHEN rp.total_pages > 1 THEN rp.total_pages ELSE COALESCE(NULLIF(b.page_count, 0), 1) END as total_pages,
        COALESCE(rp.progress_percent, 0.0) as progress_percent,
        rp.epub_cfi,
        rp.last_read_at,
        COALESCE(rp.is_favorite, 0) as is_favorite,
        COALESCE(rp.status, 'unread') as status
    FROM books b
    LEFT JOIN reading_progress rp ON b.id = rp.book_id
    WHERE b.id = ?
    """, (book_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_categories_with_counts() -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT category, COUNT(*) as count 
    FROM books 
    GROUP BY category 
    ORDER BY count DESC, category ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"category": r["category"], "count": r["count"]} for r in rows]

def get_languages() -> List[str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DISTINCT language 
    FROM books 
    WHERE language IS NOT NULL AND language != ''
    ORDER BY language ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [r["language"] for r in rows]

def get_stats() -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    
    # Purge any orphaned progress
    cursor.execute("DELETE FROM reading_progress WHERE book_id NOT IN (SELECT id FROM books)")
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) as total_books FROM books")
    total_books = cursor.fetchone()["total_books"]
    
    cursor.execute("SELECT COUNT(*) as total_reading FROM reading_progress rp JOIN books b ON rp.book_id = b.id WHERE rp.status = 'reading'")
    total_reading = cursor.fetchone()["total_reading"]
    
    cursor.execute("SELECT COUNT(*) as total_favorites FROM reading_progress rp JOIN books b ON rp.book_id = b.id WHERE rp.is_favorite = 1")
    total_favorites = cursor.fetchone()["total_favorites"]
    
    cursor.execute("SELECT COUNT(*) as total_completed FROM reading_progress rp JOIN books b ON rp.book_id = b.id WHERE rp.status = 'completed'")
    total_completed = cursor.fetchone()["total_completed"]
    
    categories = get_categories_with_counts()
    
    cursor.execute("""
    SELECT 
        b.id, b.filename, b.title, b.author, b.year, b.category, b.language,
        b.format, b.page_count, b.rel_path, b.abs_path,
        rp.current_page, CASE WHEN rp.total_pages > 1 THEN rp.total_pages ELSE COALESCE(NULLIF(b.page_count, 0), 1) END as total_pages, rp.progress_percent, rp.last_read_at
    FROM reading_progress rp
    JOIN books b ON rp.book_id = b.id
    WHERE rp.status = 'reading'
    ORDER BY rp.last_read_at DESC
    LIMIT 1
    """)
    last_read_row = cursor.fetchone()
    current_reading = dict(last_read_row) if last_read_row else None
    
    conn.close()
    return {
        "total_books": total_books,
        "total_reading": total_reading,
        "total_favorites": total_favorites,
        "total_completed": total_completed,
        "categories": categories,
        "languages": get_languages(),
        "current_reading": current_reading
    }

def update_reading_progress(
    book_id: int,
    current_page: int,
    total_pages: Optional[int] = None,
    epub_cfi: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT total_pages FROM reading_progress WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    
    cursor.execute("SELECT page_count FROM books WHERE id = ?", (book_id,))
    book_row = cursor.fetchone()
    book_page_count = book_row["page_count"] if book_row else 0
    
    final_total = total_pages or (row["total_pages"] if row and row["total_pages"] > 1 else (book_page_count or 1))
    if final_total < 1:
        final_total = 1
        
    progress_pct = min(100.0, round((current_page / final_total) * 100.0, 1))
    status = "completed" if progress_pct >= 99.0 else "reading"
    
    cursor.execute("""
    INSERT INTO reading_progress (book_id, current_page, total_pages, progress_percent, epub_cfi, last_read_at, status)
    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    ON CONFLICT(book_id) DO UPDATE SET
        current_page = excluded.current_page,
        total_pages = CASE WHEN excluded.total_pages > 1 THEN excluded.total_pages ELSE reading_progress.total_pages END,
        progress_percent = excluded.progress_percent,
        epub_cfi = COALESCE(excluded.epub_cfi, reading_progress.epub_cfi),
        last_read_at = CURRENT_TIMESTAMP,
        status = excluded.status
    """, (book_id, current_page, final_total, progress_pct, epub_cfi, status))
    
    # Always update page_count in books table when learned from reader
    if total_pages and total_pages > 1:
        cursor.execute("UPDATE books SET page_count = ? WHERE id = ?", (total_pages, book_id))
    
    conn.commit()
    conn.close()
    return get_book_by_id(book_id)

def toggle_favorite(book_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_favorite FROM reading_progress WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    
    if row:
        new_fav = 0 if row["is_favorite"] == 1 else 1
        cursor.execute("UPDATE reading_progress SET is_favorite = ? WHERE book_id = ?", (new_fav, book_id))
    else:
        new_fav = 1
        cursor.execute("""
        INSERT INTO reading_progress (book_id, is_favorite, current_page, total_pages, status)
        VALUES (?, 1, 1, 1, 'unread')
        """, (book_id,))
        
    conn.commit()
    conn.close()
    return get_book_by_id(book_id)

def update_book_metadata(
    book_id: int,
    new_title: str,
    new_author: str,
    new_year: Optional[str] = "XXXX"
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    book = get_book_by_id(book_id)
    if not book:
        return None, "Livro não encontrado"
        
    old_abs_path = Path(book["abs_path"])
    if not old_abs_path.exists():
        return None, f"Arquivo físico não encontrado no disco: {old_abs_path}"
        
    def format_part(text: str) -> str:
        t = re.sub(r'[\/\\:*?"<>|]', ' ', text).strip()
        words = t.split()
        return "_".join(w.capitalize() for w in words)
        
    year_str = (new_year or "XXXX").strip()
    if not re.match(r'^\d{4}$', year_str):
        year_str = "XXXX"
        
    title_formatted = format_part(new_title)
    author_formatted = format_part(new_author)
    ext = old_abs_path.suffix.lower()
    
    new_filename = f"({year_str}) {title_formatted} - {author_formatted}{ext}"
    new_abs_path = old_abs_path.parent / new_filename
    
    if old_abs_path != new_abs_path:
        if new_abs_path.exists():
            return None, f"Já existe um arquivo com esse nome no diretório: {new_filename}"
        try:
            old_abs_path.rename(new_abs_path)
        except Exception as e:
            return None, f"Erro ao renomear arquivo físico no disco: {str(e)}"
            
    lib_dir = get_library_dir()
    rel_path = str(new_abs_path.relative_to(lib_dir)) if lib_dir and new_abs_path.is_relative_to(lib_dir) else new_abs_path.name
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE books 
    SET title = ?, author = ?, year = ?, filename = ?, abs_path = ?, rel_path = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (new_title.strip(), new_author.strip(), year_str, new_filename, str(new_abs_path), rel_path, book_id))
    conn.commit()
    conn.close()
    
    return get_book_by_id(book_id), None

def move_book(
    book_id: int,
    new_category: str,
    new_language: str
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    book = get_book_by_id(book_id)
    if not book:
        return None, "Livro não encontrado"
        
    old_abs_path = Path(book["abs_path"])
    if not old_abs_path.exists():
        return None, f"Arquivo físico não encontrado no disco: {old_abs_path}"
        
    lib_dir = get_library_dir()
    if not lib_dir or not lib_dir.exists():
        return None, "Diretório raiz da biblioteca não está configurado."
        
    target_dir = lib_dir / new_category / new_language
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_abs_path = target_dir / book["filename"]
    
    if old_abs_path != target_abs_path:
        if target_abs_path.exists():
            return None, f"Já existe um arquivo com esse nome na pasta de destino: {target_abs_path.name}"
        try:
            shutil.move(str(old_abs_path), str(target_abs_path))
        except Exception as e:
            return None, f"Erro ao mover arquivo no disco: {str(e)}"
            
    rel_path = str(target_abs_path.relative_to(lib_dir))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE books 
    SET category = ?, language = ?, abs_path = ?, rel_path = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (new_category, new_language, str(target_abs_path), rel_path, book_id))
    conn.commit()
    conn.close()
    
    return get_book_by_id(book_id), None

def reset_reading_progress(book_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE reading_progress 
    SET status = 'unread', current_page = 1, progress_percent = 0.0, epub_cfi = NULL
    WHERE book_id = ?
    """, (book_id,))
    conn.commit()
    conn.close()
    return get_book_by_id(book_id)
