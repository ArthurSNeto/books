import sys
import sqlite3
import re
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_library_dir
from app.database import get_db

KNOWN_AUTHORS = [
    'Max Heindel', 'Steve Deace', 'Nigel Pennick', 'Alan Barbieri', 'Paul Sedir', 'Arthur Powell',
    'Ricardo Lindemann', 'Cristina Guedes', 'Amanda Celli', 'Nineveh Shadrach', 'S Connolly', 'S. Connolly',
    'Astolfo Olegario De Oliveira Filho', 'Chico Xavier', 'Allan Kardec', 'Divaldo Franco', 'Zibia Gasparetto',
    'Augusto Cury', 'Paulo Vieira', 'Gary Chapman', 'Roberto Shinyashiki', 'Jordan Peterson', 'Jordan B. Peterson',
    'Tiago Brunet', 'Steve Chandler', 'David Niven', 'Amy Morin', 'Louise Hay', 'Deepak Chopra', 'Kevin Leman'
]

def clean_doc_id_record(book: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    fn = book['filename'].strip()
    title = book['title'].strip()
    author = book['author'].strip()
    year = book['year'].strip() or 'XXXX'
    
    stem = Path(fn).stem
    # strip (XXXX) or (1988) if present
    m_yr = re.match(r'^\((\d{4}|XXXX)\)\s*(.*)$', stem)
    if m_yr:
        year = m_yr.group(1)
        stem = m_yr.group(2).strip()
        
    # Check if stem or title starts with 5+ digits
    has_id = False
    m_stem = re.match(r'^(\d{5,})[-_ ]+(.*)$', stem)
    m_title = re.match(r'^(\d{5,})[-_ ]+(.*)$', title)
    
    if m_stem:
        has_id = True
        doc_id = m_stem.group(1)
        rest = m_stem.group(2)
    elif m_title:
        has_id = True
        doc_id = m_title.group(1)
        rest = m_title.group(2)
    elif re.match(r'^\d{5,}$', title):
        has_id = True
        doc_id = title
        rest = author
    else:
        return None
        
    # Clean rest
    rest_clean = re.sub(r'\s*-\s*Autor[_ ]Desconhecido$', '', rest, flags=re.IGNORECASE).strip()
    rest_clean = re.sub(r'-pdf$', '', rest_clean, flags=re.IGNORECASE).strip()
    rest_clean = re.sub(r'^\d{5,}[-_ ]+', '', rest_clean).strip() # In case nested id
    
    # Split slug
    words = [w.strip() for w in re.split(r'[-_ ]+', rest_clean) if w.strip()]
    if not words:
        words = ["Livro", doc_id]
        
    new_title = " ".join(w.capitalize() for w in words)
    new_author = author
    if not new_author or 'desconhecido' in new_author.lower():
        new_author = 'Autor Desconhecido'
        
    # Check if author is embedded in title
    for ka in KNOWN_AUTHORS:
        ka_words = ka.lower().split()
        if all(kw in new_title.lower() for kw in ka_words):
            new_author = ka
            pattern = re.compile(re.escape(ka), re.IGNORECASE)
            new_title = pattern.sub('', new_title).strip(' -_')
            break
            
    # Format words for filename
    def format_part(text: str) -> str:
        t = re.sub(r'[\/\\:*?"<>|]', ' ', text).strip()
        return "_".join(w.capitalize() for w in t.split())
        
    title_formatted = format_part(new_title)
    author_formatted = format_part(new_author)
    ext = Path(fn).suffix.lower() or '.pdf'
    
    new_filename = f"({year}) {title_formatted} - {author_formatted}{ext}"
    
    return {
        'id': book['id'],
        'old_fn': fn,
        'old_abs_path': Path(book['abs_path']),
        'new_filename': new_filename,
        'new_title': new_title,
        'new_author': new_author,
        'year': year,
        'category': book['category'],
        'language': book['language']
    }

def run_clean_doc_ids(dry_run: bool = False):
    lib_dir = get_library_dir()
    if not lib_dir or not lib_dir.exists():
        print("Biblioteca não configurada!")
        return
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, title, author, year, category, language, rel_path, abs_path FROM books")
    books = [dict(r) for r in cursor.fetchall()]
    
    to_clean = []
    for b in books:
        res = clean_doc_id_record(b)
        if res:
            to_clean.append(res)
            
    print(f"Encontrados {len(to_clean)} livros com IDs numéricos para limpeza.")
    
    renamed_count = 0
    errors = []
    
    for item in to_clean:
        old_path = item['old_abs_path']
        new_filename = item['new_filename']
        new_path = old_path.parent / new_filename
        
        rel_path = str(new_path.relative_to(lib_dir)) if new_path.is_relative_to(lib_dir) else new_filename
        
        if dry_run:
            print(f"[DRY-RUN] ID {item['id']}: '{item['old_fn']}' -> '{new_filename}'")
            print(f"          Título: '{item['new_title']}' | Autor: '{item['new_author']}'")
            renamed_count += 1
            continue
            
        # Physical rename
        if old_path.exists():
            if old_path != new_path:
                counter = 2
                base_stem = new_path.stem
                while new_path.exists() and new_path != old_path:
                    new_filename = f"{base_stem}_{counter}{new_path.suffix}"
                    new_path = old_path.parent / new_filename
                    counter += 1
                rel_path = str(new_path.relative_to(lib_dir))
                try:
                    old_path.rename(new_path)
                except Exception as e:
                    errors.append(f"Erro ao renomear arquivo {old_path}: {e}")
                    continue
        else:
            if not new_path.exists():
                errors.append(f"Arquivo físico não encontrado: {old_path}")
                continue
                
        # Update database
        cursor.execute("""
        UPDATE books 
        SET filename = ?, title = ?, author = ?, year = ?, abs_path = ?, rel_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (new_filename, item['new_title'], item['new_author'], item['year'], str(new_path), rel_path, item['id']))
        renamed_count += 1
        
    if not dry_run:
        conn.commit()
    conn.close()
    
    print(f"\nConcluído! {renamed_count} livros processados com sucesso.")
    if errors:
        print(f"{len(errors)} avisos/erros:")
        for err in errors[:10]:
            print("  ", err)

if __name__ == '__main__':
    import sys
    dry = '--dry-run' in sys.argv
    run_clean_doc_ids(dry_run=dry)
