import sys
import sqlite3
import re
import os
import shutil
import unicodedata
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict, Any, List, Tuple
from pypdf import PdfReader

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_library_dir
from app.database import get_db
from app.scanner import scan_and_sync_library

# Stopwords dictionaries for frequency scoring
STOPWORDS = {
    'Portugues': {
        'de', 'a', 'o', 'e', 'do', 'da', 'em', 'um', 'para', 'com', 'nao', 'uma', 'os', 'no', 'se', 'na', 'por',
        'mais', 'as', 'dos', 'como', 'mas', 'ao', 'ele', 'das', 'seu', 'sua', 'ou', 'quando', 'muito', 'nos',
        'ja', 'eu', 'tambem', 'so', 'pelo', 'pela', 'ate', 'isso', 'ela', 'entre', 'depois', 'sem', 'mesmo',
        'aos', 'seus', 'quem', 'nas', 'me', 'esse', 'eles', 'voce', 'essa', 'num', 'nem', 'suas', 'meu', 'minha',
        'numa', 'pelos', 'elas', 'qual', 'lhe', 'deles', 'essas', 'esses', 'pelas', 'este', 'dele', 'tu', 'te',
        'voces', 'vos', 'lhes', 'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'sao', 'foi', 'era', 'estava',
        'estao', 'ter', 'tem', 'havia', 'sobre', 'onde', 'porque', 'livro', 'capitulo', 'vida', 'espirito',
        'homem', 'mulher', 'mundo', 'tempo', 'amor', 'morte', 'deus', 'corpo', 'mente', 'alma', 'forca'
    },
    'Ingles': {
        'the', 'and', 'of', 'to', 'in', 'a', 'is', 'that', 'for', 'it', 'as', 'was', 'with', 'on', 'be', 'by',
        'at', 'this', 'are', 'from', 'or', 'have', 'an', 'they', 'which', 'one', 'you', 'were', 'her', 'all',
        'she', 'there', 'would', 'their', 'we', 'him', 'been', 'has', 'when', 'who', 'will', 'more', 'no',
        'if', 'out', 'so', 'said', 'what', 'its', 'about', 'into', 'than', 'them', 'can', 'only', 'other',
        'new', 'some', 'could', 'time', 'these', 'two', 'may', 'then', 'do', 'first', 'any', 'my', 'now',
        'such', 'like', 'our', 'over', 'man', 'me', 'even', 'most', 'made', 'after', 'also', 'did', 'many',
        'before', 'must', 'through', 'back', 'years', 'where', 'much', 'your', 'way', 'well', 'down', 'should',
        'book', 'chapter', 'life', 'world', 'power', 'magic', 'mind', 'body', 'soul', 'god', 'death', 'love'
    },
    'Espanhol': {
        'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'para', 'con', 'no',
        'una', 'su', 'al', 'lo', 'como', 'mas', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'si', 'porque', 'esta',
        'entre', 'quando', 'muy', 'sin', 'sobre', 'tambien', 'me', 'hasta', 'hay', 'donde', 'quien', 'desde',
        'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra', 'otros', 'ese', 'eso', 'ante', 'ellos',
        'esto', 'mi', 'antes', 'algunos', 'unos', 'yo', 'otro', 'otras', 'otra', 'tanto',
        'esa', 'estos', 'mucho', 'quienes', 'nada', 'muchos', 'cual', 'sea', 'poco', 'ella', 'estar', 'haber',
        'libro', 'capitulo', 'vida', 'espiritu', 'hombre', 'mujer', 'mundo', 'tiempo', 'amor', 'muerte', 'dios'
    },
    'Frances': {
        'de', 'la', 'le', 'et', 'les', 'des', 'en', 'un', 'du', 'une', 'que', 'est', 'pour', 'qui', 'dans',
        'par', 'sur', 'au', 'plus', 'ce', 'pas', 'ne', 'se', 'avec', 'sont', 'il', 'ou', 'aux', 'comme',
        'mais', 'son', 'nous', 'cette', 'sa', 'ils', 'tout', 'on', 'ses', 'apres', 'ete', 'deux', 'aussi',
        'leur', 'bien', 'ces', 'sans', 'fait', 'elle', 'memes', 'encore', 'autre', 'temps', 'si',
        'livre', 'chapitre', 'vie', 'monde', 'homme', 'femme', 'dieu', 'mort', 'amour'
    },
    'Alemao': {
        'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'des', 'auf', 'für', 'ist', 'im',
        'dem', 'nicht', 'ein', 'eine', 'als', 'auch', 'es', 'an', 'werden', 'aus', 'er', 'hat', 'dass', 'sie',
        'nach', 'wird', 'bei', 'einer', 'um', 'am', 'sind', 'noch', 'wie', 'einem', 'über', 'einen', 'so',
        'zum', 'war', 'haben', 'nur', 'oder', 'aber', 'vor', 'zur', 'bis', 'mehr', 'durch', 'man', 'sein',
        'buch', 'kapitel', 'leben', 'welt', 'mensch', 'gott', 'tod', 'liebe'
    },
    'Italiano': {
        'di', 'il', 'la', 'che', 'in', 'per', 'un', 'del', 'della', 'dei', 'delle', 'nel', 'nella',
        'si', 'da', 'con', 'non', 'le', 'gli', 'ha', 'era', 'sono', 'ma', 'come', 'se', 'su', 'al', 'alla',
        'anche', 'piu', 'questo', 'questa', 'quello', 'tutto', 'suo', 'sua', 'loro', 'ed', 'uno', 'una',
        'libro', 'capitolo', 'vita', 'mondo', 'uomo', 'donna', 'dio', 'morte', 'amore'
    },
    'Latim': {
        'et', 'in', 'est', 'non', 'ad', 'ut', 'cum', 'de', 'sed', 'per', 'qui', 'quae', 'quod', 'aut', 'si',
        'ex', 'ab', 'etiam', 'nec', 'sunt', 'enim', 'eius', 'eum', 'iam', 'hoc', 'tam', 'nunc', 'sic', 'te'
    }
}

SURVIVAL_KEYWORDS = [
    r'\b(bushcraft|survivalism|survivalist|prepper|preppers|prepping|sobrevivencialismo|sobrevivencialista)\b',
    r'\b(manual de sobrevivencia|guia de sobrevivencia|sas survival|survival handbook|outdoor survival|wilderness survival)\b',
    r'\b(dave canterbury|bear grylls|john wiseman|lofty wiseman|cody lundin|tom brown jr|ray mears|mors kochanski|les stroud)\b',
    r'\b(bushcraft 101|bushcraft first aid|advanced bushcraft|bushcraft field guide)\b'
]

SPIRITUAL_EXCLUSIONS = [
    'espirito', 'espiritos', 'alma', 'mediunidade', 'pos-morte', 'alem', 'desencarn'
]

def normalize(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()

def normalize_words(text: str) -> List[str]:
    if not text:
        return []
    nfkd = unicodedata.normalize('NFKD', text)
    cleaned = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return [w.strip() for w in re.findall(r'[a-z]+', cleaned) if len(w) > 1]

def extract_pdf_words(pdf_path: Path, max_pages: int = 15) -> List[str]:
    if not pdf_path.exists() or pdf_path.suffix.lower() != '.pdf':
        return []
    try:
        reader = PdfReader(str(pdf_path))
        num_pages = len(reader.pages)
        all_words = []
        for i in range(min(num_pages, max_pages)):
            try:
                txt = reader.pages[i].extract_text()
                if txt:
                    all_words.extend(normalize_words(txt))
                if len(all_words) >= 300:
                    break
            except Exception:
                continue
        return all_words
    except Exception:
        return []

def detect_book_language(book: dict) -> str:
    abs_path = Path(book['abs_path'])
    title = book['title']
    fn = book['filename']
    current_lang = book['language']
    comb_norm = normalize(f"{title} {fn}")
    
    # Check if explicit translation in title
    if 'traduzido' in comb_norm or 'em portugues' in comb_norm or '(portugues)' in comb_norm:
        return 'Portugues'
        
    # 1. Try reading PDF words
    pdf_words = extract_pdf_words(abs_path)
    if len(pdf_words) >= 40:
        scores = {l: sum(1 for w in pdf_words if w in s) for l, s in STOPWORDS.items()}
        best_lang, best_score = max(scores.items(), key=lambda x: x[1])
        if best_score >= 12 and (best_score / len(pdf_words)) > 0.08:
            return best_lang

    # 2. Linguistic scoring on Title & Filename
    title_words = normalize_words(f"{title} {fn}")
    if title_words:
        scores = {l: sum(1 for w in title_words if w in s) for l, s in STOPWORDS.items()}
        best_lang, best_score = max(scores.items(), key=lambda x: x[1])
        if best_score >= 2:
            return best_lang
            
    # Portuguese special accents in title
    if re.search(r'[ãõçê]', f"{title} {fn}", re.IGNORECASE):
        return 'Portugues'
        
    # Specific language markers in title
    if re.search(r'\b(the|and|of|in|to|for|with|guide|handbook|how to|secrets of|magic|witchcraft|tarot|spells)\b', comb_norm):
        return 'Ingles'
    if re.search(r'\b(el|los|las|del|libro|guia|secretos|introduccion|manual de)\b', comb_norm):
        return 'Espanhol'
    if re.search(r'\b(le|la|les|du|des|pour|livre|histoire|traite)\b', comb_norm):
        return 'Frances'
    if re.search(r'\b(der|die|das|und|ein|eine|buch)\b', comb_norm):
        return 'Alemao'
    if re.search(r'\b(il|gli|della|delle|degli|libro)\b', comb_norm):
        return 'Italiano'
        
    return current_lang or 'Portugues'

def check_survival_category(book: dict) -> Optional[str]:
    comb = normalize(f"{book['title']} {book['author']} {book['filename']}")
    if any(re.search(p, comb) for p in SURVIVAL_KEYWORDS):
        if not any(exc in comb for exc in SPIRITUAL_EXCLUSIONS):
            # Special case: 'guia de sobrevivencia para vitimas de narcisistas' -> Psychology
            if 'vitimas' in comb or 'narcis' in comb or 'relacion' in comb:
                return None
            return "Survival_and_Bushcraft"
    return None

def clean_empty_dirs(path: Path):
    for root, dirs, files in os.walk(path, topdown=False):
        p = Path(root)
        if p != path and not any(p.iterdir()):
            try:
                p.rmdir()
            except Exception:
                pass

def run_reorganization(dry_run: bool = False):
    lib_dir = get_library_dir()
    if not lib_dir or not lib_dir.exists():
        print("Biblioteca não configurada!")
        return
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, title, author, year, category, language, rel_path, abs_path FROM books")
    books = [dict(r) for r in cursor.fetchall()]
    
    moves = []
    summary_lang = defaultdict(int)
    summary_cat = defaultdict(int)
    
    print(f"Total de livros a analisar no acervo: {len(books)}")
    
    for b in books:
        new_cat = check_survival_category(b) or b['category']
        new_lang = detect_book_language(b)
        
        if new_cat != b['category'] or new_lang != b['language']:
            moves.append((b, new_cat, new_lang))
            if new_cat != b['category']:
                summary_cat[(b['category'], new_cat)] += 1
            if new_lang != b['language']:
                summary_lang[(b['language'], new_lang)] += 1
                
    print(f"\nTotal de livros que serão ajustados: {len(moves)}")
    
    print("\n--- Mudanças de Categorias ---")
    for (src, dst), count in sorted(summary_cat.items(), key=lambda x: x[1], reverse=True):
        print(f"  {src:<35} -> {dst:<30}: {count:>4} livros")
        
    print("\n--- Mudanças de Pastas de Idioma ---")
    for (src, dst), count in sorted(summary_lang.items(), key=lambda x: x[1], reverse=True):
        print(f"  {src:<15} -> {dst:<15}: {count:>4} livros")
        
    if dry_run:
        print("\n[DRY-RUN] Primeiras 30 movimentações:")
        for b, new_cat, new_lang in moves[:30]:
            print(f"  ID {b['id']:<5} | [{b['category']}/{b['language']}] -> [{new_cat}/{new_lang}] | {b['title'][:40]}")
        conn.close()
        return
        
    print("\nExecutando movimentações físicas no disco e sincronizando SQLite...")
    moved_count = 0
    errors = []
    
    for b, new_cat, new_lang in moves:
        old_abs_path = Path(b['abs_path'])
        filename = b['filename']
        
        target_dir = lib_dir / new_cat / new_lang
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_abs_path = target_dir / filename
        
        # Handle file rename/move collision safely
        if old_abs_path != target_abs_path:
            if target_abs_path.exists():
                counter = 2
                stem = Path(filename).stem
                ext = Path(filename).suffix
                while target_abs_path.exists() and target_abs_path != old_abs_path:
                    filename = f"{stem}_{counter}{ext}"
                    target_abs_path = target_dir / filename
                    counter += 1
                    
            if old_abs_path.exists():
                try:
                    shutil.move(str(old_abs_path), str(target_abs_path))
                except Exception as e:
                    errors.append(f"Erro ao mover '{old_abs_path}': {e}")
                    continue
            else:
                if not target_abs_path.exists():
                    errors.append(f"Arquivo não encontrado: '{old_abs_path}'")
                    continue
                    
        rel_path = str(target_abs_path.relative_to(lib_dir))
        
        cursor.execute("""
        UPDATE books 
        SET category = ?, language = ?, filename = ?, abs_path = ?, rel_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (new_cat, new_lang, filename, str(target_abs_path), rel_path, b['id']))
        moved_count += 1
        
    conn.commit()
    conn.close()
    
    print(f"\nConcluído com sucesso! {moved_count} livros movidos e atualizados.")
    if errors:
        print(f"{len(errors)} avisos/erros encontrados:")
        for err in errors[:10]:
            print("  ", err)
            
    # Clean up empty dirs
    clean_empty_dirs(lib_dir)
    
    # Final library scan
    print("\nExecutando escaneamento final da biblioteca...")
    scan_and_sync_library()

if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    run_reorganization(dry_run=dry)
