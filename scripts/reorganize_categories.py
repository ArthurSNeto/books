import sys
import sqlite3
import re
import os
import shutil
import unicodedata
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict, Any, List, Tuple

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_library_dir
from app.database import get_db

def normalize(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()

# =========================================================================
# CATEGORY DEFINITIONS AND RULES
# =========================================================================

# 1. SPIRITISM & MEDIUMSHIP (Allan Kardec, Chico Xavier, Divaldo Franco, Robson Pinheiro, etc.)
SPIRITISM_AUTHORS = [
    'allan kardec', 'kardec', 'chico xavier', 'francisco candido xavier', 'divaldo franco', 'divaldo pereira franco',
    'zibia gasparetto', 'leon denis', 'jose herculano pires', 'herculano pires', 'eliana machado coelho',
    'elisa masselli', 'richard simonetti', 'ernesto bozzano', 'yvonne a. pereira', 'yvonne pereira',
    'vera lucia marinzeck de carvalho', 'vera lucia marinzeck', 'cairbar schutel', 'marcelo cezar', 'marcelo cezar',
    'monica de castro', 'carlos a. baccelli', 'carlos baccelli', 'saara nousiainen', 'osmar barbosa',
    'camille flammarion', 'amadeu ribeiro', 'umberto fabbri', 'robson pinheiro', 'astolfo olegario de oliveira filho',
    'mauro kwitko', 'luiz guilherme marques', 'andré luiz', 'andre luiz', 'emmanuel', 'miramez',
    'manoel philomeno de miranda', 'manoel p. de miranda', 'rodrigo queiroz espirita', 'wera krynian',
    'ademir mendonca', 'ademir mendonça', 'luiz roberto mattos', 'valdelice salum', 'alziro zarur', 'paiva netto',
    'nair lages', 'marcio godinho', 'marilusa vasconcellos', 'joao nunes maia', 'jorge hessen', 'pietro ubaldi',
    'gabriel delanne', 'james van praagh', 'wilson frungilo jr', 'hernani guimaraes andrade', 'edgard armond',
    'irene pacheco machado', 'celia xavier camargo', 'celia xavier', 'fernando ben', 'lilian campos',
    'humberto de campos', 'irmao x', 'neio lucio', 'meimei', 'joanna de angelis', 'patricia psicografia',
    'luiz sergio', 'mauricio de castro', 'batuira', 'euripedes barsanulfo', 'adolfo bezerra de menezes',
    'bezerra de menezes', 'arthur powell', 'charles leadbeater espirito', 'annie besant espirito'
]

SPIRITISM_KEYWORDS = [
    'espiritismo', 'kardec', 'kardecista', 'kardequiano', 'chico xavier', 'divaldo franco', 'zibia gasparetto',
    'psicografia', 'psicografado', 'psicografada', 'desobsessao', 'doutrina espirita', 'plano espiritual',
    'passe espirita', 'centro espirita', 'evangelho segundo o espiritismo', 'livro dos espiritos', 'livro dos mediuns',
    'mensagens espiritas', 'romance espirita', 'mundo espiritual', 'colonia espiritual', 'nosso lar',
    'mediunidade', 'vida no mundo espiritual', 'obreiros da vida eterna', 'missionarios da luz',
    'evolucao em dois mundos', 'mecanismos da mediunidade', 'no mundo maior', 'sexo e destino',
    'e a vida continua', 'psicofonia', 'fluidoterapia', 'desdobramento espiritual', 'apometria',
    'regressao de memoria', 'terapia de vidas passadas', 'reencarnacao', 'colonia nosso lar',
    'mansao do caminho', 'feb federacao', 'federacao espirita', 'transicao planetaria chico xavier',
    'transicao planetaria', 'apice da transicao planetaria', 'licoes sobre mediunidade'
]

# 2. PSYCHOLOGY & SELF HELP (Augusto Cury, Paulo Vieira, Dale Carnegie, Gary Chapman, etc.)
SELF_HELP_AUTHORS = [
    'augusto cury', 'paulo vieira', 'gary chapman', 'roberto shinyashiki', 'jordan peterson', 'jordan b. peterson',
    'tiago brunet', 'steve chandler', 'david niven', 'amy morin', 'louise hay', 'louise l. hay', 'deepak chopra',
    'kevin leman', 'fabricio carpinejar', 'samantha silvany', 'dale carnegie', 'napoleon hill', 'lair ribeiro',
    'mark manson', 'charles duhigg', 'brene brown', 'hal elrod', 'tony robbins', 'anthony robbins',
    'robert kiyosaki', 't. harv eker', 'tim ferriss', 'stephen r. covey', 'stephen covey', 'eckhart tolle',
    'james clear', 'carol dweck', 'damrong pinkoon', 'claiton e sie', 'gustavo cerbasi', 'joseph murphy',
    'irvin d. yalom', 'mirian goldenberg', 'luiz antonio gasparetto', 'adenauer novaes', 'ana cristina vargas',
    'cinthia cortegoso', 'sonia tozzi', 'marcos lacerda', 'pedro calabrez', 'rossandro clinjey',
    'leandro karnal', 'mario sergio cortella', 'clovis de barros filho', 'flavio augusto',
    'conrado adolpho', 'cairo santos', 'sigmund freud', 'carl jung', 'c.g. jung', 'carl gustav jung',
    'wilhelm reich', 'jacques lacan', 'donald winnicott', 'melanie klein', 'viktor frankl', 'erich fromm',
    'daniel goleman', 'mihaly csikszentmihalyi', 'william ury', 'robert cialdini', 'chris voss', 'simon sinek',
    'bruce lipton', 'joe dispenza', 'gregg braden', 'rhonda byrne', 'esther hicks', 'jerry hicks', 'abraham hicks',
    'neville goddard', 'florence scovel shinn', 'wallace d. wattles', 'bob proctor', 'john maxwell',
    'gabriel o pensador autoajuda', 'martha medeiros'
]

SELF_HELP_KEYWORDS = [
    'autoajuda', 'habitos atomicos', 'habito', 'habitos', 'mindset', 'inteligencia emocional', 'poder do habito',
    'como fazer amigos', 'pai rico pai pobre', 'milagre da manha', 'segredos da mente milionaria',
    '12 regras para a vida', 'ansiedade como enfrentar', 'gestao da emocao', 'pais brilhantes',
    'comunicacao nao violenta', 'desperte seu gigante interior', '5 linguagens do amor', 'as 5 linguagens',
    'cinco linguagens', 'autoestima', 'pensamento positivo', 'relacionamento abusivo', 'atrair dinheiro',
    'lei da atracao', 'hooponopono', 'ho\'oponopono', 'inteligencia financeira', 'casais inteligentes',
    'segredos das pessoas felizes', 'maneiras de motivar', 'como convencer alguem', 'comunicacao assertiva',
    'o poder do agora', 'o poder do subconsciente', 'a sutil arte de ligar', 'foco e produtividade',
    'gerenciamento do tempo', 'inteligencia interpessoal', 'resiliencia', 'psicologia positiva',
    'terapia cognitivo', 'psicoterapia', 'superando o luto', 'amor proprio', 'rejeicao amorosa',
    'casamento blindado', 'inteligencia multifocal', 'ansiedade', 'depressao', 'sindrome do panico',
    'burnout', 'terapia de casal', 'terapia familiar', 'educar filhos', 'regras de ouro para educar',
    'curar sua vida', 'atualizar sua vida', 'vida extraordinaria', 'mudar uma vida', 'pessoas mentalmente fortes',
    'dias de poder', 'ideias do pensamento positivo', 'se livrar de um relacionamento', 'dias sem voce'
]

# 3. EASTERN PHILOSOPHY & BUDDHISM (Buddhism, Taoism, Hinduism, Meditation, Feng Shui)
EASTERN_AUTHORS = [
    'thich nhat hanh', 'dalai lama', 'osho', 'alan watts', 'krishnamurti', 'jiddu krishnamurti',
    'paramahansa yogananda', 'yogananda', 'swami vivekananda', 'sri aurobindo', 'lao tse', 'lao tzu',
    'sun tzu', 'chögyam trungpa', 'chogyam trungpa', 'suzuki', 'dt suzuki', 'd. t. suzuki',
    'ryuho okawa', 'ramana maharshi', 'nisargadatta maharaj', 'sadhguru', 'buddha', 'bodhidharma',
    'shunryu suzuki', 'matthieu ricard', 'pema chodron', 'mooji', 'papaji', 'silvana occhialini'
]

EASTERN_KEYWORDS = [
    'budismo', 'budista', 'buda', 'zen budismo', 'taoismo', 'tao te ching', 'tao-te-king',
    'mindfulness', 'meditacao vipassana', 'hinduismo', 'bhagavad gita', 'upanishads', 'vedas',
    'yoga sutras', 'patanjali', 'kundalini yoga', 'hatha yoga', 'dharma', 'karma yoga',
    'mantras tibetanos', 'livro tibetano dos mortos', 'bardo thodol', 'samadhi', 'satori',
    'advaita vedanta', 'feng shui'
]

# 4. DIVINATION & ORACLES (Astrology, Tarot, Runes, Lenormand, Palmistry, I Ching)
DIVINATION_AUTHORS = [
    'chris brennan', 'liz greene', 'stephen arroyo', 'dane rudhyar', 'howard sasportas', 'robert hand',
    'hajo banzhaf', 'nei naiff', 'arthur edward waite', 'rachel pollack', 'mary k. greer',
    'robert m. place', 'sasha graham', 'alejandro jodorowsky', 'claudia lisboa', 'marcelo del debbio taro'
]

DIVINATION_KEYWORDS = [
    'astrologia', 'horoscopo', 'mapa astral', 'signos do zodiaco', 'astrologica', 'astrologico',
    'casas astrologicas', 'planetas e signos', 'astrologia helenistica', 'astrologia vedica',
    'hellenistic astrology', 'tarot', 'taro', 'arcanos maiores', 'arcanos menores', 'cartomancia',
    'baralho cigano', 'lenormand', 'quiromancia', 'leitura de maos', 'runas futhark', 'runas nordicas',
    'oraculo', 'oraculos', 'radiestesia e radionica', 'pendulo hebreu', 'geomancia',
    'numerologia cabalistica', 'numerologia pitagorica', 'manual of cheirosophy'
]

# 5. AFRO-BRAZILIAN & DIASPORA (Umbanda, Candomblé, Quimbanda, Hoodoo, Voodoo)
AFRO_AUTHORS = [
    'rubens saraceni', 'alan barbieri', 'rodrigo queiroz', 'f. rivas neto', 'wamiri albuquerque',
    'alexandre cumino', 'norberto peixoto', 'antonio alves teixeira', 'jose ribeiro de souza',
    'altair b. oliveira', 'reginaldo prandi', 'roger farias', 'diego de oxossi'
]

AFRO_KEYWORDS = [
    'umbanda', 'candomble', 'quimbanda', 'orixa', 'orixas', 'pombagira', 'pomba gira', 'exu',
    'tranca ruas', 'marabô', 'sete encruzilhadas', 'ze pelintra', 'pretos velhos', 'caboclos',
    'terreiro de umbanda', 'pontos cantados', 'pontos riscados', 'ebos', 'macumba', 'hoodoo',
    'voodoo', 'ifa dida', 'caminhos de odu', 'adimu', 'patipembas', 'conjure'
]

# 6. WITCHCRAFT & PAGANISM (Wicca, Traditional Witchcraft, Sabats)
WITCHCRAFT_AUTHORS = [
    'gerald gardner', 'scott cunningham', 'raymond buckland', 'silver ravenwolf', 'laurie cabot',
    'doreen valiente', 'eddie van feu', 'claudiney prieto', 'starhawk', 'janet farrar', 'stewart farrar',
    'christopher penczak', 'judika illes', 'phyllis curott', 'marian green', 'raven grimassi'
]

WITCHCRAFT_KEYWORDS = [
    'wicca', 'wiccano', 'bruxaria', 'bruxa', 'bruxo', 'grimorio da bruxa', 'livro das sombras',
    'deusa triplice', 'paganismo', 'sagrado feminino', 'feiticaria tradicional', 'sabats',
    'esbats', 'magia natural e bruxaria', 'covens', 'coven', 'witcheshandbook'
]

# 7. NATURAL MEDICINE & HERBS (Phytotherapy, Herbal baths, Crystals, Aromatherapy)
HERBS_AUTHORS = [
    'amanda celli', 'adolfo perez agusti', 'alessio facchin', 'maria treben'
]

HERBS_KEYWORDS = [
    'banho de ervas', 'banhos magicos de ervas', 'plantas medicinais', 'fitoterapia',
    'fitoenergetica', 'aromaterapia', 'cristais de cura', 'oleos essenciais',
    'florais de bach', 'ervas sagradas', 'remedios caseiros', 'ervas que curam',
    'ervas e banhos', '508 banhos'
]

# 8. CONSPIRACIES & UFOLOGY (Ufology, Ancient Aliens, Conspiracies)
UFO_AUTHORS = [
    'zecharia sitchin', 'erich von daniken', 'erich von däniken', 'david icke', 'j. j. benitez',
    'jj benitez', 'gregorio valdez', 'adolfo scherhag'
]

UFO_KEYWORDS = [
    'alienigenas', 'anunnaki', 'ufo', 'ufologia', 'discos voadores', 'extraterrestres',
    'illuminati', 'conspiracao mundial', 'operacao prato', 'area 51'
]

# 9. PHILOSOPHY, HISTORY & MYTHOLOGY (Greek/Roman/Egyptian Mythology, Classic Philosophy)
MYTHOLOGY_AUTHORS = [
    'menelaos stephanides', 'mircea eliade', 'joseph campbell', 'platao', 'aristoteles',
    'socrates', 'friedrich nietzsche', 'nietzsche', 'arthur schopenhauer', 'schopenhauer',
    'immanuel kant', 'kant', 'rene descartes', 'baruch spinoza', 'spinoza', 'soren kierkegaard',
    'martin heidegger', 'michel foucault', 'jean-paul sartre', 'albert camus'
]

MYTHOLOGY_KEYWORDS = [
    'mitologia grega', 'mitologia nordica', 'mitologia egipcia', 'filosofia grega',
    'historia antiga', 'historia de roma', 'historia do egito', 'epopeia de gilgamesh',
    'mahabharata', 'ramayana', 'iliada', 'odisseia', 'dialogos de platao', 'a republica'
]

# 10. FICTION
FICTION_KEYWORDS = [
    'harry potter', 'senhor dos aneis', 'game of thrones', 'cronicas de gelo e fogo',
    'dan brown', 'o codigo da vinci', 'anjos e demonios', 'deborah harkness', 'o livro da vida',
    'christian jacq asilo de assassinos', 'ficcao cientifica'
]

# 11. CHRISTIANITY / GENERAL SPIRITUALITY
CHRISTIAN_AUTHORS = [
    'luciano subira', 'tiago brunet pastoral', 'max lucado', 'c.s. lewis', 'cs lewis',
    'timothy keller', 'augustine', 'tomas de aquino', 'padre fabio de melo', 'padre marcelo rossi',
    'edir macedo', 'r.r. soares', 'silas malafaia', 'hernandes dias lopes'
]

CHRISTIAN_KEYWORDS = [
    'biblia sagrada', 'jesus cristo', 'evangelho de cristo', 'catolicismo', 'teologia crista',
    'santo agostinho', 'sao tomas de aquino', 'devocional diario', 'oracoes catolicas',
    'historia da igreja', 'concilio de niceia', 'salmos biblicos'
]

def classify_book(book: Dict[str, Any]) -> Optional[str]:
    norm_title = normalize(book['title'])
    norm_author = normalize(book['author'])
    norm_file = normalize(book['filename'])
    combined = f"{norm_title} {norm_author} {norm_file}"
    
    # Priority matching order:
    
    # 1. Spiritism (major misclassified cluster)
    if any(a in norm_author for a in SPIRITISM_AUTHORS) or any(w in combined for w in SPIRITISM_KEYWORDS):
        return "Spiritism_and_Mediumship"
        
    # 2. Self Help / Psychology / Personal Development / Coaching
    if any(a in norm_author for a in SELF_HELP_AUTHORS) or any(w in combined for w in SELF_HELP_KEYWORDS):
        return "Psychology_and_Self_Help"
        
    # 3. Eastern Religions, Buddhism & Meditation
    if any(a in norm_author for a in EASTERN_AUTHORS) or any(w in combined for w in EASTERN_KEYWORDS):
        return "Eastern_Philosophy_and_Buddhism"
        
    # 4. Divination / Astrology / Tarot / Oracles
    if any(a in norm_author for a in DIVINATION_AUTHORS) or any(w in combined for w in DIVINATION_KEYWORDS):
        return "Divination_and_Oracles"
        
    # 5. Afro-Brazilian & Diaspora
    if any(a in norm_author for a in AFRO_AUTHORS) or any(w in combined for w in AFRO_KEYWORDS):
        return "Afro_Brazilian_and_Diaspora_Religions"
        
    # 6. Witchcraft & Paganism
    if any(a in norm_author for a in WITCHCRAFT_AUTHORS) or any(w in combined for w in WITCHCRAFT_KEYWORDS):
        return "Witchcraft_and_Paganism"
        
    # 7. Natural Medicine, Herbs & Crystals
    if any(a in norm_author for a in HERBS_AUTHORS) or any(w in combined for w in HERBS_KEYWORDS):
        return "Natural_Medicine_and_Herbs"
        
    # 8. Ufology & Conspiracies
    if any(a in norm_author for a in UFO_AUTHORS) or any(w in combined for w in UFO_KEYWORDS):
        return "Conspiracies_and_Ufology"
        
    # 9. Fiction
    if any(w in combined for w in FICTION_KEYWORDS):
        return "Fiction"
        
    # 10. Ancient Mythology & Classical Philosophy
    if any(a in norm_author for a in MYTHOLOGY_AUTHORS) or any(w in combined for w in MYTHOLOGY_KEYWORDS):
        return "Philosophy_History_and_Mythology"
        
    # 11. Christianity / General Spirituality
    if any(a in norm_author for a in CHRISTIAN_AUTHORS) or any(w in combined for w in CHRISTIAN_KEYWORDS):
        return "Spirituality_and_Religions"
        
    return None # Stays in Occultism_and_Esotericism

def run_reorganization(dry_run: bool = False):
    lib_dir = get_library_dir()
    if not lib_dir or not lib_dir.exists():
        print("Biblioteca não configurada!")
        return
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, filename, title, author, year, category, language, rel_path, abs_path 
    FROM books 
    WHERE category = 'Occultism_and_Esotericism'
    """)
    books = [dict(r) for r in cursor.fetchall()]
    
    moves = []
    category_counts = defaultdict(int)
    
    for b in books:
        new_cat = classify_book(b)
        if new_cat and new_cat != b['category']:
            moves.append((b, new_cat))
            category_counts[new_cat] += 1
            
    print(f"Total de livros analisados em Occultism_and_Esotericism: {len(books)}")
    print(f"Total de livros para mover: {len(moves)}")
    print("\nResumo das movimentações por categoria de destino:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  -> {cat:<36}: {count} livros")
    print(f"  -> Permanecem em Occultism_and_Esotericism: {len(books) - len(moves)} livros")
    
    if dry_run:
        print("\n[DRY-RUN] Exibindo primeiras 25 movimentações de amostra:")
        for b, new_cat in moves[:25]:
            print(f"  ID {b['id']:<5} | '{b['title'][:40]}' | '{b['author'][:25]}' -> {new_cat}")
        conn.close()
        return
        
    print("\nExecutando movimentações físicas no disco e sincronizando SQLite...")
    moved_count = 0
    errors = []
    
    for b, new_cat in moves:
        old_abs_path = Path(b['abs_path'])
        lang = b['language'] or 'Portugues'
        filename = b['filename']
        
        target_dir = lib_dir / new_cat / lang
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_abs_path = target_dir / filename
        
        # Handle collision
        if old_abs_path != target_abs_path:
            if target_abs_path.exists():
                counter = 2
                stem = Path(filename).stem
                ext = Path(filename).suffix
                while target_abs_path.exists():
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
                    errors.append(f"Arquivo físico de origem não encontrado: '{old_abs_path}'")
                    continue
                    
        rel_path = str(target_abs_path.relative_to(lib_dir))
        
        # Update database
        cursor.execute("""
        UPDATE books 
        SET category = ?, filename = ?, abs_path = ?, rel_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (new_cat, filename, str(target_abs_path), rel_path, b['id']))
        moved_count += 1
        
    conn.commit()
    conn.close()
    
    print(f"\nConcluído com sucesso! {moved_count} livros movidos.")
    if errors:
        print(f"{len(errors)} avisos/erros encontrados:")
        for err in errors[:10]:
            print("  ", err)

if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    run_reorganization(dry_run=dry)
