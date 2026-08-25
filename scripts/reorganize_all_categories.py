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
# COMPREHENSIVE CATEGORY RULES WITH STRONG DOMAIN SAFEGUARDS
# =========================================================================

BUSINESS_AUTHORS = [
    'david allen', 'steven kotler', 'adam grant', 'daniel kahneman', 'ken honda', 'stephen a. schwarzman',
    'stephen schwarzman', 'gustavo cerbasi', 'mary buffett', 'mary buff', 'elainne ourives',
    'napoleon hill', 'robert kiyosaki', 'george s. clason', 'thiago nigro', 'luiz barsi', 'warren buffett',
    'peter drucker', 'stephen r. covey', 'stephen covey', 'charles duhigg', 'james clear',
    'tim ferriss', 't. harv eker', 'brian tracy', 'dan lok', 'grant cardone', 'jeff sutherland', 'eric ries',
    'flavio augusto', 'conrado adolpho', 'cairo santos', 'john c. maxwell', 'john maxwell', 'jim collins',
    'simon sinek', 'gary vee', 'gary vaynerchuk', 'alex hormozi', 'mj demarco', 'ramit sethi', 'caito maia',
    'nathalia arcuri', 'pedro suassuna', 'tiago reis', 'dan ariely', 'richard thaler', 'nassim nicholas taleb',
    'nassim taleb', 'ray dalio', 'morgan housel', 'howard marks', 'benjamin graham', 'philip fisher',
    'seth godin', 'phil knight', 'satya nadella', 'reed hastings', 'peter thiel', 'ben horowitz',
    'al ries', 'jack trout', 'robert cialdini', 'chris voss', 'john perry'
]

BUSINESS_PATTERNS = [
    r'\b(fazer acontecer|getting things done|a arte de fazer acontecer|a arte do impossivel|a arte da procrastinacao)\b',
    r'\b(dar e receber|rapido e devagar|como chegar la|faca como warren buffett|investimentos inteligentes)\b',
    r'\b(casais inteligentes enriquecem|dna milionario|dinheiro feliz|o homem mais rico da babilonia|pai rico pai pobre)\b',
    r'\b(segredos da mente milionaria|os segredos da mente milionaria|quem pensa enriquece|inteligencia financeira)\b',
    r'\b(independencia financeira|liberdade financeira|renda passiva|acoes e dividendos|mercado financeiro)\b',
    r'\b(bolsa de valores|educacao financeira|financas pessoais|planejamento financeiro|mente milionaria)\b',
    r'\b(do mil ao milhao|me poupe|fator enriquecimento|startup enxuta|metodo agile|scrum|kanban)\b',
    r'\b(growth hacking|funil de vendas|copywriting|planejamento estrategico|microeconomia|macroeconomia)\b',
    r'\b(financas corporativas|analise fundamentalista|day trade|criptomoedas|bitcoin|blockchain e negocios)\b'
]

HEALTH_AUTHORS = [
    'dr. danny penman', 'danny penman', 'alexis brink', 'valcapelli',
    'william davis', 'david perlmutter', 'tim spector', 'jason fung', 'dr. barakat', 'lara briden',
    'mark hyman', 'michael greger', 'dr. lair ribeiro', 'arnold ehret',
    'norman walker', 'max gerson', 'matthew walker', 'steven gundry', 'peter attia', 'david sinclair',
    'valter longo', 'dr. juliano pimentel', 'tiago rocha biologo', 'alexandre rocha',
    'drauzio varella', 'ana claudia quintana arantes', 'bruce fife', 'kelly starrett'
]

HEALTH_PATTERNS = [
    r'\b(metafisica da saude|a arte de respirar|a arte do jin shin|jin shin jyutsu)\b',
    r'\b(barriga de trigo|grao na cabeca|dieta cetogenica|dieta low carb|dieta mediterranea)\b',
    r'\b(jejum intermitente|alimentacao saudavel|reeducacao alimentar|nutricao funcional)\b',
    r'\b(medicina preventiva|microbiota intestinal|longevidade saudavel|ciencia do sono)\b',
    r'\b(biohacking|otimizacao da saude|emagrecimento definitivo|emagreca sem dieta)\b',
    r'\b(codigo da obesidade|codigo do diabetes|saude cardiovascular|cerebro sem fome)\b',
    r'\b(exercicios posturais|anatomia do movimento|metodo wim hof|respiracao consciente)\b',
    r'\b(saude hormonal|menopausa sem misterio|saude da tireoide)\b'
]

RELATIONSHIPS_AUTHORS = [
    'henrik fexeus', 'phillip mcgregor', 'philip mcgregor', 'luiz hanns', 'leila ferreira',
    'nelio tombini', 'emma reed turrell', 'fabrice midal', 'barbara berckhan', 'robert holden',
    'julia cameron', 'kevin leman', 'john gottman', 'esther perel', 'allan pease', 'barbara pease',
    'joe navarro', 'elisama santos', 'louis burlamaqui', 'john gray', 'harriet lerner',
    'sue johnson', 'amir levine', 'rachel heller', 'martha medeiros',
    'marcos lacerda', 'ana beatriz barbosa silva', 'albert j. bernstein', 'carol kinsey goman',
    'cornelia topf'
]

RELATIONSHIPS_PATTERNS = [
    r'\b(a arte de ler mentes|a arte de ler pessoas|a arte de dar limites|a arte de se agradar)\b',
    r'\b(a arte de ser infeliz|a arte de ser leve|a arte francesa de mandar tudo|a arte de fazer escolhas)\b',
    r'\b(a arte de amar e ser amado|arte de se fazer respeitar|a arte da escuta|educacao nao violenta)\b',
    r'\b(sete segredos que ele nunca vai contar|entre lencois|vampiros emocionais|a linguagem corporal dos lideres)\b',
    r'\b(linguagem corporal para mulheres|o corpo fala|manual de persuasao do fbi|desvende os segredos da linguagem)\b',
    r'\b(homens sao de marte, mulheres sao de venus|homens sao de marte mulheres sao de venus)\b',
    r'\b(as 5 linguagens do amor|cinco linguagens do amor|linguagens do amor das criancas)\b',
    r'\b(casamento blindado|terapia de casal|terapia familiar|como salvar seu casamento)\b',
    r'\b(relacionamento saudavel|relacionamentos toxicos|dependencia emocional|apego ansioso|apegados)\b',
    r'\b(inteligencia amorosa|educar sem gritar|pais que ajudam filhos|disciplina positiva)\b',
    r'\b(por que os homens fazem sexo e as mulheres fazem amor)\b'
]

PSYCHOLOGY_AUTHORS = [
    'rolf dobelli', 'alberto dell\'isola', 'alberto dellisola', 'daniel j. siegel', 'mauro hegenberg',
    'richard wiseman', 'dan harris', 'regina giannetti', 'augusto cury', 'paulo块vieira', 'paulo vieira',
    'roberto shinyashiki', 'jordan peterson', 'jordan b. peterson', 'tiago brunet', 'steve chandler',
    'david niven', 'amy morin', 'louise hay', 'deepak chopra', 'fabricio carpinejar', 'samantha silvany',
    'brene brown', 'hal elrod', 'tony robbins', 'eckhart tolle', 'carol dweck', 'damrong pinkoon',
    'claiton e sie', 'joseph murphy', 'irvin d. yalom', 'mirian goldenberg', 'luiz antonio gasparetto',
    'adenauer novaes', 'ana cristina vargas', 'cinthia cortegoso', 'sonia tozzi', 'pedro calabrez',
    'rossandro clinjey', 'sigmund freud', 'carl jung', 'c.g. jung', 'carl gustav jung', 'wilhelm reich',
    'jacques lacan', 'donald winnicott', 'melanie klein', 'viktor frankl', 'erich fromm', 'daniel goleman',
    'mihaly csikszentmihalyi', 'bruce lipton', 'joe dispenza', 'gregg braden', 'rhonda byrne', 'esther hicks',
    'abraham hicks', 'neville goddard', 'florence scovel shinn', 'wallace d. wattles', 'bob proctor',
    'jim kwik', 'abrahao grinberg', 'baltasar gracian', 'stephen arterburn'
]

PSYCHOLOGY_PATTERNS = [
    r'\b(a arte de pensar claramente|a arte da imperfeicao|mentes geniais|cerebro adolescente)\b',
    r'\b(59 segundos|10 mais feliz|que voce esteja bem|borderline|sem limites jim kwik)\b',
    r'\b(a arte de envelhecer com sabedoria|a arte da sabedoria|autoajuda|habitos atomicos)\b',
    r'\b(inteligencia emocional|poder do habito|como fazer amigos|12 regras para a vida)\b',
    r'\b(ansiedade como enfrentar|gestao da emocao|pais brilhantes|desperte seu gigante interior)\b',
    r'\b(autoestima|pensamento positivo|hooponopono|segredos das pessoas felizes|maneiras de motivar)\b',
    r'\b(o poder do agora|o poder do subconsciente|a sutil arte de ligar|psicologia positiva)\b',
    r'\b(terapia cognitivo|psicoterapia|superando o luto|amor proprio|inteligencia multifocal)\b',
    r'\b(ansiedade|depressao|sindrome do panico|burnout|curar sua vida|atualizar sua vida)\b',
    r'\b(vida extraordinaria|mudar uma vida|pessoas mentalmente fortes|dias de poder|paredes emocionais)\b'
]

FICTION_AUTHORS = [
    'christian jacq', 'jennifer l. armentrout', 'jan-philipp sendker', 'richard kelly',
    'bernard evslin', 'dan brown', 'stephen king', 'j.k. rowling', 'george r.r. martin',
    'j.r.r. tolkien', 'bernard cornwell', 'neil gaiman', 'agatha christie', 'arthur conan doyle',
    'clarice lispector', 'machado de assis', 'jorge amado', 'paulo coelho', 'guimaraes rosa',
    'andrei fernandes', 'deborah harkness'
]

FICTION_PATTERNS = [
    r'\b(a arte de ouvir o coracao|serie ramess|serie ramses|saga lux|kalciferum)\b',
    r'\b(donnie darko|herois deuses e monstros bernard evslin|cronicas de arthur|cronicas de artur)\b',
    r'\b(cronicas de gelo e fogo|senhor dos aneis|o hobbit|harry potter|codigo da vinci)\b',
    r'\b(anjos e demonios|inferno dan brown|origem dan brown|o livro da vida)\b',
    r'\b(sob a acacia do ocidente|a batalha de kadesh|o templo de milhoes de anos)\b'
]

EASTERN_AUTHORS = [
    'william hart', 'amber hatch', 'nobuo suzuki', 'michael a. singer', 'michel a. singer',
    'thich nhat hanh', 'dalai lama', 'osho', 'alan watts', 'krishnamurti', 'jiddu krishnamurti',
    'paramahansa yogananda', 'yogananda', 'swami vivekananda', 'sri aurobindo', 'lao tse', 'lao tzu',
    'sun tzu', 'chögyam trungpa', 'chogyam trungpa', 'suzuki', 'dt suzuki', 'd. t. suzuki',
    'ryuho okawa', 'ramana maharshi', 'nisargadatta maharaj', 'sadhguru', 'buddha', 'bodhidharma',
    'shunryu suzuki', 'matthieu ricard', 'pema chodron', 'mooji', 'papaji', 'silvana occhialini'
]

EASTERN_PATTERNS = [
    r'\b(a arte de viver william hart|a arte do silencio amber hatch|ganbatte nobuo suzuki)\b',
    r'\b(alma livre michel a. singer|the untethered soul|budismo|zen budismo|taoismo)\b',
    r'\b(tao te ching|vipassana|meditacao vipassana|mindfulness|feng shui|upanishads)\b',
    r'\b(bhagavad gita|kundalini|yoga sutras|patanjali|advaita vedanta|samadhi|satori)\b',
    r'\b(autobiografia de um iogue|essencia de buda|ensinamentos de buda)\b'
]

SPIRITISM_AUTHORS = [
    'j. w. rochester', 'christina nunes', 'osmar barbosa', 'jorge hessen', 'pietro ubaldi',
    'geziel andrade', 'luiz guilherme marques', 'allan kardec', 'chico xavier', 'divaldo franco',
    'zibia gasparetto', 'leon denis', 'jose herculano pires', 'herculano pires', 'eliana machado coelho',
    'elisa masselli', 'richard simonetti', 'ernesto bozzano', 'yvonne a. pereira', 'vera lucia marinzeck',
    'cairbar schutel', 'marcelo cezar', 'monica de castro', 'carlos a. baccelli', 'saara nousiainen',
    'camille flammarion', 'amadeu ribeiro', 'umberto fabbri', 'robson pinheiro', 'astolfo olegario',
    'mauro kwitko', 'andré luiz', 'andre luiz', 'emmanuel', 'miramez', 'manoel philomeno de miranda',
    'joao nunes maia', 'gabriel delanne', 'james van praagh', 'wilson frungilo jr', 'hernani guimaraes andrade',
    'edgard armond', 'irene pacheco machado', 'celia xavier camargo', 'fernando ben', 'lilian campos',
    'humberto de campos', 'irmao x', 'joanna de angelis', 'euripedes barsanulfo', 'bezerra de menezes'
]

SPIRITISM_PATTERNS = [
    r'\b(vos sois deuses|sonata ao amor|mae voltei|logo deus existe|grandes mensagens)\b',
    r'\b(espiritismo|kardec|kardecista|chico xavier|divaldo franco|zibia gasparetto)\b',
    r'\b(psicografia|desobsessao|doutrina espirita|plano espiritual|passe espirita)\b',
    r'\b(evangelho segundo o espiritismo|livro dos espiritos|livro dos mediuns|romance espirita)\b',
    r'\b(mundo espiritual|colonia espiritual|nosso lar|mediunidade|vida no mundo espiritual)\b',
    r'\b(reencarnacao|apometria|terapia de vidas passadas|transicao planetaria)\b'
]

CHRISTIAN_AUTHORS = [
    'jacob boehme', 'joseph tissot', 'timothy keller', 'max lucado', 'sao tomas de aquino',
    'santo agostinho', 'teresa de avila', 'sao joao da cruz', 'mestre eckhart', 'c.s. lewis',
    'cs lewis', 'lutero', 'calvino', 'spurgeon', 'luciano subira', 'tiago brunet pastoral',
    'padre fabio de melo', 'padre marcelo rossi', 'edir macedo', 'hernandes dias lopes'
]

CHRISTIAN_PATTERNS = [
    r'\b(confissoes jacob boehme|arvore da fe crista|a arte de aproveitar se das proprias faltas)\b',
    r'\b(deuses falsos|mundo plural timothy keller|biblia sagrada|jesus cristo|evangelho de cristo)\b',
    r'\b(catolicismo|teologia crista|santo agostinho|sao tomas de aquino|devocional diario)\b'
]

PHILOSOPHY_AUTHORS = [
    'neil price', 'ryan holiday', 'menelaos stephanides', 'mircea eliade', 'joseph campbell',
    'platao', 'aristoteles', 'socrates', 'friedrich nietzsche', 'nietzsche', 'arthur schopenhauer',
    'schopenhauer', 'immanuel kant', 'kant', 'rene descartes', 'baruch spinoza', 'spinoza',
    'soren kierkegaard', 'martin heidegger', 'michel foucault', 'jean-paul sartre', 'albert camus',
    'seneca', 'marco aurelio', 'epicteto'
]

PHILOSOPHY_PATTERNS = [
    r'\b(vikings neil price|diario estoico|mitologia grega|mitologia nordica|mitologia egipcia)\b',
    r'\b(filosofia grega|historia antiga|historia de roma|historia do egito|epopeia de gilgamesh)\b',
    r'\b(dialogos de platao|a republica platao|meditacoes marco aurelio|manual de epicteto)\b'
]

# Protected domains
AFRO_KEYWORDS = [
    'umbanda', 'candomble', 'quimbanda', 'orixa', 'orixas', 'pombagira', 'pomba gira', 'exu',
    'tranca ruas', 'marabo', 'sete encruzilhadas', 'ze pelintra', 'pretos velhos', 'caboclos',
    'terreiro', 'aruanda', 'pontos cantados', 'pontos riscados', 'ebos', 'macumba', 'hoodoo',
    'voodoo', 'ifa dida', 'caminhos de odu', 'adimu', 'patipembas', 'conjure', 'saraceni',
    'alan barbieri', 'norberto peixoto'
]

WITCHCRAFT_KEYWORDS = [
    'wicca', 'wiccano', 'bruxaria', 'bruxa', 'bruxo', 'grimorio da bruxa', 'livro das sombras',
    'deusa triplice', 'paganismo', 'sagrado feminino', 'feiticaria tradicional', 'sabats', 'esbats'
]

TRUE_OCCULT_KEYWORDS = [
    'hermet', 'thelema', 'crowley', 'eliphas levi', 'papus', 'franz bardon', 'regardie',
    'dion fortune', 'blavatsky', 'goetia', 'alquimi', 'alchemy', 'enochian', 'enochiano',
    'qabalah', 'kabbalah', 'cabala', 'zohar', 'rosacruz', 'rosa-cruz', 'maconaria', 'macom',
    'lucifer', 'demonologia', 'magick', 'magia cerimonial', 'magia do caos'
]

def classify_book(b: Dict[str, Any]) -> Optional[str]:
    norm_t = normalize(b['title'])
    norm_a = normalize(b['author'])
    norm_f = normalize(b['filename'])
    comb = f"{norm_t} {norm_a} {norm_f}"
    current_cat = b['category']
    
    # Generic self-help/relationship authors that should be moved regardless of where they are
    if any(a in norm_a for a in ['augusto cury', 'john gray', 'henrik fexeus', 'phillip mcgregor', 'fabrice midal', 'leila ferreira', 'nelio tombini', 'emma reed turrell', 'luiz hanns', 'kevin leman', 'gary chapman', 'david allen', 'gustavo cerbasi', 'ken honda', 'daniel kahneman', 'adam grant', 'fabricio carpinejar', 'samantha silvany', 'dale carnegie', 'jordan peterson', 'steve chandler', 'david niven', 'amy morin', 'louise hay', 'deepak chopra saude', 'dan harris', 'regina giannetti', 'alberto dell\'isola', 'alberto dellisola', 'richard wiseman']):
        # Classify by specific domain
        if any(a in norm_a for a in BUSINESS_AUTHORS) or any(re.search(p, comb) for p in BUSINESS_PATTERNS):
            return "Business_and_Finance"
        if any(a in norm_a for a in RELATIONSHIPS_AUTHORS) or any(re.search(p, comb) for p in RELATIONSHIPS_PATTERNS):
            return "Relationships_and_Communication"
        return "Psychology_and_Self_Help"

    # SAFEGUARD 1: Afro Brazilian Traditions (Terreiro, Orixás, Umbanda, Candomblé, Quimbanda, Exu, Hoodoo)
    if any(w in comb for w in AFRO_KEYWORDS):
        return 'Afro_Brazilian_and_Diaspora_Religions'
            
    # SAFEGUARD 2: Witchcraft & Paganism (Wicca, Bruxaria, Sabats, Deusa Tríplice)
    if any(w in comb for w in WITCHCRAFT_KEYWORDS):
        return 'Witchcraft_and_Paganism'
        
    # Check Fiction
    if any(a in norm_a for a in FICTION_AUTHORS) or any(a in comb for a in FICTION_AUTHORS) or any(re.search(p, comb) for p in FICTION_PATTERNS):
        return "Fiction"
        
    # Check Business & Finance
    if any(a in norm_a for a in BUSINESS_AUTHORS) or any(a in comb for a in BUSINESS_AUTHORS) or any(re.search(p, comb) for p in BUSINESS_PATTERNS):
        return "Business_and_Finance"
        
    # Check Health & Wellness
    if any(a in norm_a for a in HEALTH_AUTHORS) or any(a in comb for a in HEALTH_AUTHORS) or any(re.search(p, comb) for p in HEALTH_PATTERNS):
        return "Health_and_Wellness"
        
    # Check Relationships & Communication
    if any(a in norm_a for a in RELATIONSHIPS_AUTHORS) or any(a in comb for a in RELATIONSHIPS_AUTHORS) or any(re.search(p, comb) for p in RELATIONSHIPS_PATTERNS):
        return "Relationships_and_Communication"
        
    # Check Spiritism & Mediumship
    if any(a in norm_a for a in SPIRITISM_AUTHORS) or any(a in comb for a in SPIRITISM_AUTHORS) or any(re.search(p, comb) for p in SPIRITISM_PATTERNS):
        return "Spiritism_and_Mediumship"
        
    # Check Eastern Philosophy & Buddhism
    if any(a in norm_a for a in EASTERN_AUTHORS) or any(a in comb for a in EASTERN_AUTHORS) or any(re.search(p, comb) for p in EASTERN_PATTERNS):
        return "Eastern_Philosophy_and_Buddhism"
        
    # Check Christianity / Spirituality
    if any(a in norm_a for a in CHRISTIAN_AUTHORS) or any(a in comb for a in CHRISTIAN_AUTHORS) or any(re.search(p, comb) for p in CHRISTIAN_PATTERNS):
        return "Spirituality_and_Religions"
        
    # Check Philosophy / History / Mythology
    if any(a in norm_a for a in PHILOSOPHY_AUTHORS) or any(a in comb for a in PHILOSOPHY_AUTHORS) or any(re.search(p, comb) for p in PHILOSOPHY_PATTERNS):
        return "Philosophy_History_and_Mythology"
        
    # Check Psychology & Self Help (general)
    if any(a in norm_a for a in PSYCHOLOGY_AUTHORS) or any(a in comb for a in PSYCHOLOGY_AUTHORS) or any(re.search(p, comb) for p in PSYCHOLOGY_PATTERNS):
        return "Psychology_and_Self_Help"
        
    # SAFEGUARD 3: True Occultism
    if any(w in comb for w in TRUE_OCCULT_KEYWORDS):
        return "Occultism_and_Esotericism"
        
    return None # Stays in current category

def run_deep_reorganization(dry_run: bool = False):
    lib_dir = get_library_dir()
    if not lib_dir or not lib_dir.exists():
        print("Biblioteca não configurada!")
        return
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, title, author, year, category, language, rel_path, abs_path FROM books")
    books = [dict(r) for r in cursor.fetchall()]
    
    moves = []
    category_summary = defaultdict(int)
    
    for b in books:
        target = classify_book(b)
        if target and target != b['category']:
            moves.append((b, target))
            category_summary[(b['category'], target)] += 1
            
    print(f"Total de livros analisados no acervo: {len(books)}")
    print(f"Total de livros a serem movidos: {len(moves)}")
    print("\n--- Resumo das Movimentações por Origem -> Destino ---")
    for (src, dst), count in sorted(category_summary.items(), key=lambda x: x[1], reverse=True):
        print(f"  {src:<36} -> {dst:<35}: {count:>4} livros")
        
    if dry_run:
        print("\n[DRY-RUN] Primeiras 30 movimentações de amostra:")
        for b, target in moves[:30]:
            print(f"  ID {b['id']:<5} | [{b['category']}] -> [{target}] | '{b['title'][:40]}' - '{b['author'][:25]}'")
        conn.close()
        return
        
    print("\nExecutando movimentações físicas no disco e sincronizando SQLite...")
    moved_count = 0
    errors = []
    
    for b, target in moves:
        old_abs_path = Path(b['abs_path'])
        lang = b['language'] or 'Portugues'
        filename = b['filename']
        
        target_dir = lib_dir / target / lang
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_abs_path = target_dir / filename
        
        # Handle collision
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
                    errors.append(f"Arquivo físico de origem não encontrado: '{old_abs_path}'")
                    continue
                    
        rel_path = str(target_abs_path.relative_to(lib_dir))
        
        cursor.execute("""
        UPDATE books 
        SET category = ?, filename = ?, abs_path = ?, rel_path = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (target, filename, str(target_abs_path), rel_path, b['id']))
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
    run_deep_reorganization(dry_run=dry)
