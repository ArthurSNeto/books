// Main Application Logic - 100% Dynamic Categories & Hybrid Library Path Support

// Intelligent Category Icon Resolver (Contextual matching with fallback)
function getCategoryIcon(catName) {
    if (!catName) return 'book-open';
    const lower = catName.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    
    if (lower.includes('business') || lower.includes('financ') || lower.includes('dinheiro') || lower.includes('invest') || lower.includes('negocio') || lower.includes('econom')) return 'trending-up';
    if (lower.includes('health') || lower.includes('diet') || lower.includes('nutri') || lower.includes('saude') || lower.includes('well') || lower.includes('fitness')) return 'heart-pulse';
    if (lower.includes('relationship') || lower.includes('relacion') || lower.includes('comunic') || lower.includes('famil') || lower.includes('casam')) return 'users';
    if (lower.includes('occult') || lower.includes('ocult') || lower.includes('hermet') || lower.includes('esoter') || lower.includes('magia') || lower.includes('magic') || lower.includes('alquimi') || lower.includes('thelema')) return 'flame';
    if (lower.includes('witch') || lower.includes('brux') || lower.includes('pagan') || lower.includes('wicca') || lower.includes('luna') || lower.includes('moon')) return 'moon';
    if (lower.includes('afro') || lower.includes('umbanda') || lower.includes('candomble') || lower.includes('orixa') || lower.includes('hoodoo') || lower.includes('voodoo') || lower.includes('ifa')) return 'feather';
    if (lower.includes('divin') || lower.includes('taro') || lower.includes('tarot') || lower.includes('oracul') || lower.includes('runa') || lower.includes('astrol') || lower.includes('quirom')) return 'eye';
    if (lower.includes('spiritism') || lower.includes('medium') || lower.includes('kardec') || lower.includes('psicograf')) return 'sparkles';
    if (lower.includes('eastern') || lower.includes('buddh') || lower.includes('orient') || lower.includes('zen') || lower.includes('tao') || lower.includes('hindu')) return 'sun';
    if (lower.includes('spirit') || lower.includes('espirit') || lower.includes('relig') || lower.includes('yoga') || lower.includes('xama') || lower.includes('crist')) return 'sparkles';
    if (lower.includes('psych') || lower.includes('psic') || lower.includes('autoajuda') || lower.includes('mente') || lower.includes('mind') || lower.includes('coach') || lower.includes('habito')) return 'brain';
    if (lower.includes('philos') || lower.includes('filo') || lower.includes('hist') || lower.includes('mito') || lower.includes('civil') || lower.includes('grego') || lower.includes('romano')) return 'landmark';
    if (lower.includes('herb') || lower.includes('plant') || lower.includes('flor') || lower.includes('natur') || lower.includes('cura') || lower.includes('medic') || lower.includes('fitoter')) return 'flower-2';
    if (lower.includes('ufo') || lower.includes('ovni') || lower.includes('alien') || lower.includes('consp') || lower.includes('extrater') || lower.includes('secreto')) return 'shield-alert';
    if (lower.includes('rare') || lower.includes('raro') || lower.includes('ban') || lower.includes('grimo') || lower.includes('proib') || lower.includes('demon') || lower.includes('manusc')) return 'skull';
    if (lower.includes('fic') || lower.includes('fant') || lower.includes('romance') || lower.includes('novel') || lower.includes('conto') || lower.includes('lit') || lower.includes('juvenil')) return 'swords';
    if (lower.includes('curs') || lower.includes('train') || lower.includes('apostil') || lower.includes('aula') || lower.includes('manual') || lower.includes('tutor') || lower.includes('educa')) return 'graduation-cap';
    if (lower.includes('art') || lower.includes('desi') || lower.includes('pint')) return 'palette';
    if (lower.includes('music') || lower.includes('som') || lower.includes('audio')) return 'music';
    if (lower.includes('cienc') || lower.includes('scien') || lower.includes('fisic') || lower.includes('quim')) return 'atom';
    if (lower.includes('prog') || lower.includes('comput') || lower.includes('tech') || lower.includes('cod')) return 'terminal';
    
    return 'folder';
}

function formatCategoryName(name) {
    if (!name) return 'Geral';
    return name.replace(/_/g, ' ').replace(/\w/g, c => c.toUpperCase());
}

let state = {
    query: '',
    category: 'all',
    language: 'all',
    format: 'all',
    status: 'all',
    favorite: null,
    page: 1,
    pageSize: 24,
    sortBy: 'title',
    sortOrder: 'asc',
    activeBook: null,
    editingBook: null,
    movingBook: null,
    isCreatingNewCategory: false,
    isCreatingNewLanguage: false,
    availableCategories: [],
    availableLanguages: []
};

let searchTimeout = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupEventListeners();
    const isConfigured = await checkConfig();
    if (isConfigured) {
        await loadStats();
        await loadLanguages();
        await loadBooks();
    }
    lucide.createIcons();
}

async function checkConfig() {
    try {
        const res = await fetch('/api/config');
        const data = await res.json();
        
        document.getElementById('libraryPathInput').value = data.library_path || '';
        
        const badge = document.getElementById('pathValidationBadge');
        if (data.exists) {
            badge.textContent = 'Conectado';
            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60';
            return true;
        } else {
            badge.textContent = 'Não Encontrado';
            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-950 text-rose-400 border border-rose-800/60';
            openSettingsModal('Para começar, informe onde estão os seus livros (pasta local ou Google Drive):');
            return false;
        }
    } catch (e) {
        console.error('Error checking config:', e);
        return false;
    }
}

function setupEventListeners() {
    // Search input with debounce
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearchBtn');
    
    searchInput.addEventListener('input', (e) => {
        state.query = e.target.value;
        state.page = 1;
        clearBtn.classList.toggle('hidden', !state.query);
        
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadBooks();
        }, 250);
    });

    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        state.query = '';
        state.page = 1;
        clearBtn.classList.add('hidden');
        loadBooks();
    });

    // Navigation buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.cat-item').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const filter = btn.dataset.filter;
            state.category = 'all';
            state.page = 1;
            
            if (filter === 'all') {
                state.status = 'all';
                state.favorite = null;
                document.getElementById('currentSectionTitle').textContent = 'Todos os Livros';
            } else if (filter === 'reading') {
                state.status = 'reading';
                state.favorite = null;
                document.getElementById('currentSectionTitle').textContent = 'Lendo Atualmente';
            } else if (filter === 'favorites') {
                state.status = 'all';
                state.favorite = true;
                document.getElementById('currentSectionTitle').textContent = 'Livros Favoritos';
            } else if (filter === 'completed') {
                state.status = 'completed';
                state.favorite = null;
                document.getElementById('currentSectionTitle').textContent = 'Livros Concluídos';
            }
            
            loadBooks();
        });
    });

    // Language filter select
    document.getElementById('languageSelect').addEventListener('change', (e) => {
        state.language = e.target.value;
        state.page = 1;
        loadBooks();
    });

    // Format filter buttons
    document.querySelectorAll('.format-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.format = btn.dataset.format;
            state.page = 1;
            loadBooks();
        });
    });

    // Sort select
    document.getElementById('sortBySelect').addEventListener('change', (e) => {
        const [col, order] = e.target.value.split('_');
        state.sortBy = col;
        state.sortOrder = order;
        state.page = 1;
        loadBooks();
    });

    // Settings Modal
    document.getElementById('settingsBtn').addEventListener('click', () => openSettingsModal());
    document.getElementById('closeSettingsModalBtn').addEventListener('click', () => document.getElementById('settingsModal').classList.add('hidden'));
    document.getElementById('cancelSettingsBtn').addEventListener('click', () => document.getElementById('settingsModal').classList.add('hidden'));
    document.getElementById('settingsForm').addEventListener('submit', handleSettingsSubmit);

    // Resync button
    document.getElementById('resyncBtn').addEventListener('click', async () => {
        showToast('Sincronizando biblioteca do disco...');
        try {
            const res = await fetch('/api/sync', { method: 'POST' });
            const data = await res.json();
            showToast(`Sincronização concluída! ${data.total_synced} livros encontrados.`);
            await loadStats();
            await loadLanguages();
            await loadBooks();
        } catch (e) {
            showToast('Erro ao sincronizar: ' + e.message, 'error');
        }
    });

    // Reader modal controls
    document.getElementById('closeReaderBtn').addEventListener('click', closeReader);
    document.getElementById('nextPageBtn').addEventListener('click', () => {
        if (state.activeBook && state.activeBook.format === 'epub') epubNextPage();
        else pdfNextPage();
    });
    document.getElementById('prevPageBtn').addEventListener('click', () => {
        if (state.activeBook && state.activeBook.format === 'epub') epubPrevPage();
        else pdfPrevPage();
    });
    document.getElementById('zoomInBtn').addEventListener('click', pdfZoomIn);
    document.getElementById('zoomOutBtn').addEventListener('click', pdfZoomOut);
    document.getElementById('readerThemeBtn').addEventListener('click', toggleReaderTheme);
    document.getElementById('readerPageInput').addEventListener('change', (e) => {
        const p = parseInt(e.target.value);
        if (state.activeBook && state.activeBook.format === 'epub') {
            if (currentEpubBook && currentEpubBook.locations && currentEpubBook.locations.total) {
                const cfi = currentEpubBook.locations.cfiFromLocation(p - 1);
                if (cfi) currentRendition.display(cfi);
            }
        } else {
            if (p >= 1 && p <= currentPdfTotalPages) renderPdfPage(p);
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById('readerModal');
        if (!modal.classList.contains('hidden')) {
            if (e.key === 'ArrowRight' || e.key === 'PageDown') {
                if (state.activeBook && state.activeBook.format === 'epub') epubNextPage();
                else pdfNextPage();
            } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
                if (state.activeBook && state.activeBook.format === 'epub') epubPrevPage();
                else pdfPrevPage();
            } else if (e.key === 'Escape') {
                closeReader();
            } else if (e.key === 'f' || e.key === 'F') {
                toggleFullscreen();
            }
        }
    });

    // Fullscreen toggle
    document.getElementById('fullscreenBtn').addEventListener('click', toggleFullscreen);

    // Edit form modal
    document.getElementById('closeEditModalBtn').addEventListener('click', () => document.getElementById('editModal').classList.add('hidden'));
    document.getElementById('cancelEditBtn').addEventListener('click', () => document.getElementById('editModal').classList.add('hidden'));
    document.getElementById('editForm').addEventListener('submit', handleEditSubmit);

    // Edit inputs live preview
    const updatePreview = () => {
        const t = document.getElementById('editTitleInput').value.trim();
        const a = document.getElementById('editAuthorInput').value.trim();
        const y = document.getElementById('editYearInput').value.trim() || 'XXXX';
        const cleanT = t.replace(/\s+/g, '_');
        const cleanA = a.replace(/\s+/g, '_');
        const ext = state.editingBook ? '.' + state.editingBook.format : '.pdf';
        document.getElementById('editFilenamePreview').textContent = `(${y}) ${cleanT} - ${cleanA}${ext}`;
    };
    document.getElementById('editTitleInput').addEventListener('input', updatePreview);
    document.getElementById('editAuthorInput').addEventListener('input', updatePreview);
    document.getElementById('editYearInput').addEventListener('input', updatePreview);

    // Move form modal
    document.getElementById('closeMoveModalBtn').addEventListener('click', () => document.getElementById('moveModal').classList.add('hidden'));
    document.getElementById('cancelMoveBtn').addEventListener('click', () => document.getElementById('moveModal').classList.add('hidden'));
    document.getElementById('moveForm').addEventListener('submit', handleMoveSubmit);

    // Toggle custom category / language in Move modal
    const toggleNewCatBtn = document.getElementById('toggleNewCategoryBtn');
    const newCatInput = document.getElementById('newCategoryInput');
    const catSelect = document.getElementById('moveCategorySelect');
    if (toggleNewCatBtn) {
        toggleNewCatBtn.addEventListener('click', () => {
            state.isCreatingNewCategory = !state.isCreatingNewCategory;
            newCatInput.classList.toggle('hidden', !state.isCreatingNewCategory);
            catSelect.classList.toggle('hidden', state.isCreatingNewCategory);
            toggleNewCatBtn.textContent = state.isCreatingNewCategory ? 'Selecionar Existente' : '+ Criar Nova';
            if (state.isCreatingNewCategory) newCatInput.focus();
            updateMovePreview();
        });
    }

    const toggleNewLangBtn = document.getElementById('toggleNewLanguageBtn');
    const newLangInput = document.getElementById('newLanguageInput');
    const langSelect = document.getElementById('moveLanguageSelect');
    if (toggleNewLangBtn) {
        toggleNewLangBtn.addEventListener('click', () => {
            state.isCreatingNewLanguage = !state.isCreatingNewLanguage;
            newLangInput.classList.toggle('hidden', !state.isCreatingNewLanguage);
            langSelect.classList.toggle('hidden', state.isCreatingNewLanguage);
            toggleNewLangBtn.textContent = state.isCreatingNewLanguage ? 'Selecionar Existente' : '+ Criar Novo';
            if (state.isCreatingNewLanguage) newLangInput.focus();
            updateMovePreview();
        });
    }

    const updateMovePreview = () => {
        const cat = state.isCreatingNewCategory ? (newCatInput.value.trim() || 'NovaCategoria') : catSelect.value;
        const lang = state.isCreatingNewLanguage ? (newLangInput.value.trim() || 'NovoIdioma') : langSelect.value;
        const filename = state.movingBook ? state.movingBook.filename : 'livro.pdf';
        document.getElementById('movePathPreview').textContent = `Books/${cat}/${lang}/${filename}`;
    };
    catSelect.addEventListener('change', updateMovePreview);
    langSelect.addEventListener('change', updateMovePreview);
    if (newCatInput) newCatInput.addEventListener('input', updateMovePreview);
    if (newLangInput) newLangInput.addEventListener('input', updateMovePreview);
}

function openSettingsModal(infoMsg = null) {
    const modal = document.getElementById('settingsModal');
    const statusMsg = document.getElementById('settingsStatusMsg');
    
    if (infoMsg) {
        statusMsg.textContent = infoMsg;
        statusMsg.className = 'text-xs p-3 rounded-xl border bg-purple-950/40 border-purple-800 text-purple-300';
        statusMsg.classList.remove('hidden');
    } else {
        statusMsg.classList.add('hidden');
    }
    
    modal.classList.remove('hidden');
    document.getElementById('libraryPathInput').focus();
    lucide.createIcons();
}

async function handleSettingsSubmit(e) {
    e.preventDefault();
    const path = document.getElementById('libraryPathInput').value.trim();
    const btn = document.getElementById('saveSettingsBtn');
    const btnText = document.getElementById('saveSettingsBtnText');
    const statusMsg = document.getElementById('settingsStatusMsg');
    
    if (!path) return;
    
    btn.disabled = true;
    btnText.textContent = 'Sincronizando...';
    statusMsg.classList.add('hidden');
    
    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ library_path: path })
        });
        
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Erro ao configurar diretório');
        }
        
        statusMsg.textContent = `Diretório configurado com sucesso! ${data.total_synced} livros encontrados.`;
        statusMsg.className = 'text-xs p-3 rounded-xl border bg-emerald-950/50 border-emerald-800 text-emerald-300';
        statusMsg.classList.remove('hidden');
        
        showToast(`Biblioteca sincronizada: ${data.total_synced} livros!`);
        
        await checkConfig();
        await loadStats();
        await loadLanguages();
        await loadBooks();
        
        setTimeout(() => {
            document.getElementById('settingsModal').classList.add('hidden');
        }, 1200);
    } catch (err) {
        statusMsg.textContent = err.message;
        statusMsg.className = 'text-xs p-3 rounded-xl border bg-rose-950/50 border-rose-800 text-rose-300';
        statusMsg.classList.remove('hidden');
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Salvar & Sincronizar';
    }
}

async function loadLanguages() {
    try {
        const res = await fetch('/api/languages');
        const languages = await res.json();
        state.availableLanguages = languages;
        
        const langSelect = document.getElementById('languageSelect');
        const moveLangSelect = document.getElementById('moveLanguageSelect');
        
        // Preserve selection if possible
        const currentSelected = langSelect.value;
        
        langSelect.innerHTML = '<option value="all">Todos os Idiomas</option>';
        moveLangSelect.innerHTML = '';
        
        languages.forEach(l => {
            const opt = document.createElement('option');
            opt.value = l;
            opt.textContent = l;
            langSelect.appendChild(opt);
            
            const opt2 = document.createElement('option');
            opt2.value = l;
            opt2.textContent = l;
            moveLangSelect.appendChild(opt2);
        });
        
        if (languages.includes(currentSelected)) {
            langSelect.value = currentSelected;
        }
    } catch (e) {
        console.error('Error loading languages:', e);
    }
}

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        state.availableCategories = data.categories || [];
        
        document.getElementById('totalBooksCount').textContent = `${data.total_books.toLocaleString()} Livros`;
        document.getElementById('navAllCount').textContent = data.total_books.toLocaleString();
        document.getElementById('navReadingCount').textContent = data.total_reading;
        document.getElementById('navFavCount').textContent = data.total_favorites;
        document.getElementById('navCompletedCount').textContent = data.total_completed;

        // Render dynamic categories in sidebar
        const catList = document.getElementById('categoriesList');
        catList.innerHTML = '';
        
        data.categories.forEach(c => {
            const btn = document.createElement('button');
            btn.className = `cat-item ${state.category === c.category ? 'active' : ''}`;
            const niceName = formatCategoryName(c.category);
            const iconName = getCategoryIcon(c.category);
            
            btn.innerHTML = `
                <div class="flex items-center gap-2.5 min-w-0 flex-1 mr-2 text-left">
                    <i data-lucide="${iconName}" class="w-4 h-4 shrink-0 text-purple-400"></i>
                    <span class="truncate font-medium text-slate-300 text-xs">${niceName}</span>
                </div>
                <span class="text-[11px] font-mono text-slate-400 shrink-0 px-2 py-0.5 rounded-md bg-[#0a0f1d] border border-slate-800/80 font-semibold">${c.count}</span>
            `;
            
            btn.addEventListener('click', () => {
                document.querySelectorAll('.cat-item').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                state.category = c.category;
                state.status = 'all';
                state.favorite = null;
                state.page = 1;
                document.getElementById('currentSectionTitle').textContent = niceName;
                loadBooks();
            });
            
            catList.appendChild(btn);
        });

        // Populate move modal category select
        const moveCatSelect = document.getElementById('moveCategorySelect');
        moveCatSelect.innerHTML = '';
        data.categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.category;
            opt.textContent = formatCategoryName(c.category);
            moveCatSelect.appendChild(opt);
        });

        // Hero "Continuar Lendo"
        const hero = document.getElementById('continueReadingHero');
        if (data.current_reading) {
            const cr = data.current_reading;
            hero.classList.remove('hidden');
            document.getElementById('heroTitle').textContent = cr.title;
            document.getElementById('heroAuthor').textContent = `${cr.author} (${cr.year})`;
            document.getElementById('heroCategory').textContent = formatCategoryName(cr.category);
            document.getElementById('heroProgressBar').style.width = `${cr.progress_percent || 0}%`;
            document.getElementById('heroProgressText').textContent = `Pág. ${cr.current_page || 1} / ${cr.total_pages || 1} (${Math.round(cr.progress_percent || 0)}%)`;
            
            document.getElementById('heroResumeBtn').onclick = () => openReader(cr);
            const dismissBtn = document.getElementById('heroDismissBtn');
            if (dismissBtn) {
                dismissBtn.onclick = async (e) => {
                    e.stopPropagation();
                    await resetBookProgress(cr.id, cr.title);
                };
            }
        } else {
            hero.classList.add('hidden');
        }
        
        lucide.createIcons();
    } catch (e) {
        console.error('Error loading stats:', e);
    }
}

async function loadBooks() {
    const grid = document.getElementById('booksGrid');
    grid.innerHTML = '<div class="col-span-full py-20 flex flex-col items-center justify-center text-slate-500 gap-3"><i data-lucide="loader-2" class="w-8 h-8 animate-spin text-purple-500"></i><span>Carregando livros...</span></div>';
    lucide.createIcons();

    try {
        const params = new URLSearchParams({
            page: state.page,
            page_size: state.pageSize,
            sort_by: state.sortBy,
            sort_order: state.sortOrder
        });

        if (state.query) params.append('q', state.query);
        if (state.category !== 'all') params.append('category', state.category);
        if (state.language !== 'all') params.append('language', state.language);
        if (state.format !== 'all') params.append('format_type', state.format);
        if (state.status !== 'all') params.append('status', state.status);
        if (state.favorite !== null) params.append('favorite', state.favorite);

        const res = await fetch(`/api/books?${params.toString()}`);
        const data = await res.json();

        document.getElementById('sectionResultsCount').textContent = `Mostrando ${data.items.length} de ${data.total.toLocaleString()} livros`;

        renderBooksGrid(data.items);
        renderPagination(data.page, data.total_pages, data.total);
    } catch (e) {
        grid.innerHTML = `<div class="col-span-full py-16 text-center text-rose-400">Erro ao carregar livros: ${e.message}</div>`;
    }
}

function renderBooksGrid(books) {
    const grid = document.getElementById('booksGrid');
    grid.innerHTML = '';

    if (books.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full py-20 flex flex-col items-center justify-center text-slate-500 gap-3 bg-[#0d1326]/40 rounded-2xl border border-slate-800">
                <i data-lucide="book-x" class="w-12 h-12 text-slate-600"></i>
                <span class="text-sm font-semibold text-slate-400">Nenhum livro encontrado</span>
                <span class="text-xs text-slate-500">Tente ajustar seus termos de busca ou filtros.</span>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    books.forEach(book => {
        const card = document.createElement('div');
        card.className = 'book-card flex flex-col justify-between group';
        
        const catNice = formatCategoryName(book.category);
        const iconName = getCategoryIcon(book.category);
        const formatBadgeColor = book.format === 'epub' ? 'bg-cyan-950 text-cyan-300 border-cyan-700/60' : 'bg-rose-950 text-rose-300 border-rose-700/60';
        const isFav = book.is_favorite === 1;

        const totalPagesCount = (book.total_pages > 1 ? book.total_pages : book.page_count) || 0;
        const totalPagesLabel = totalPagesCount > 0 ? `${totalPagesCount} págs` : '';

        card.innerHTML = `
            <div class="flex items-start justify-between gap-2">
                <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${formatBadgeColor} uppercase tracking-wider">
                    ${book.format}
                </span>
                <div class="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 font-semibold">
                    ${totalPagesLabel ? `<span class="text-slate-400">${totalPagesLabel}</span><span class="text-slate-600">•</span>` : ''}
                    <span>${book.year || 'XXXX'}</span>
                </div>
            </div>

            <div class="flex flex-col gap-1 my-1">
                <h4 class="text-sm font-bold text-white group-hover:text-purple-300 transition-colors line-clamp-2 title-tooltip leading-tight" title="${book.title}">
                    ${book.title}
                </h4>
                <p class="text-xs text-slate-400 font-medium line-clamp-1" title="${book.author}">
                    ${book.author}
                </p>
            </div>

            <!-- TAGS WITHOUT TOP BORDER -->
            <div class="flex items-center gap-1.5 flex-wrap text-[11px] text-slate-400 pt-0.5">
                <span class="px-2 py-0.5 rounded-md bg-[#0a0f1e] border border-slate-800/80 truncate max-w-[140px]" title="${catNice}">
                    ${catNice}
                </span>
                <span class="px-2 py-0.5 rounded-md bg-[#0a0f1e] border border-slate-800/80">
                    ${book.language || 'Geral'}
                </span>
                ${book.progress_percent > 0 ? `
                    <span class="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 font-bold">
                        Pág. ${book.current_page} / ${totalPagesCount || book.total_pages}
                    </span>
                ` : ''}
            </div>

            ${book.progress_percent > 0 ? `
                <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden border border-slate-800 mt-1">
                    <div class="bg-gradient-to-r from-purple-500 to-emerald-400 h-full rounded-full" style="width: ${book.progress_percent}%"></div>
                </div>
            ` : ''}

            <div class="flex items-center gap-1.5 mt-auto pt-2">
                <button class="read-btn flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-md shadow-purple-950/40 transition-all hover:scale-[1.02] active:scale-95">
                    <i data-lucide="book-open" class="w-3.5 h-3.5"></i>
                    <span>Ler</span>
                </button>
                <button class="edit-btn p-2 rounded-xl bg-[#12192e] hover:bg-[#1a2544] text-slate-400 hover:text-white border border-slate-800 transition-colors" title="Editar Título / Metadados">
                    <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                </button>
                <button class="move-btn p-2 rounded-xl bg-[#12192e] hover:bg-[#1a2544] text-slate-400 hover:text-white border border-slate-800 transition-colors" title="Mover Categoria / Idioma">
                    <i data-lucide="folder-input" class="w-3.5 h-3.5"></i>
                </button>
                <button class="fav-btn p-2 rounded-xl bg-[#12192e] hover:bg-[#1a2544] ${isFav ? 'text-amber-400' : 'text-slate-400'} hover:text-amber-400 border border-slate-800 transition-colors" title="Favoritar">
                    <i data-lucide="star" class="w-3.5 h-3.5 ${isFav ? 'fill-amber-400' : ''}"></i>
                </button>
                ${book.progress_percent > 0 ? `
                    <button class="reset-read-btn p-2 rounded-xl bg-[#12192e] hover:bg-rose-950/80 text-slate-400 hover:text-rose-300 border border-slate-800 hover:border-rose-800/60 transition-colors" title="Remover de Continuar Lendo">
                        <i data-lucide="bookmark-x" class="w-3.5 h-3.5"></i>
                    </button>
                ` : ''}
            </div>
        `;

        card.querySelector('.read-btn').addEventListener('click', () => openReader(book));
        card.querySelector('.edit-btn').addEventListener('click', () => openEditModal(book));
        card.querySelector('.move-btn').addEventListener('click', () => openMoveModal(book));
        card.querySelector('.fav-btn').addEventListener('click', () => toggleFav(book.id));
        const resetBtn = card.querySelector('.reset-read-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => resetBookProgress(book.id, book.title));
        }

        grid.appendChild(card);
    });

    lucide.createIcons();
}

function renderPagination(currentPage, totalPages, totalItems) {
    const infoEl = document.getElementById('paginationInfo');
    const controlsEl = document.getElementById('paginationControls');
    
    if (infoEl) {
        infoEl.textContent = `Página ${currentPage} de ${totalPages} (${totalItems.toLocaleString()} livros)`;
    }
    
    if (!controlsEl) return;
    controlsEl.innerHTML = '';

    if (totalPages <= 1) return;

    // Prev button
    const prevBtn = document.createElement('button');
    prevBtn.className = `p-2 rounded-xl bg-[#0d1326] border border-slate-800 text-slate-400 hover:text-white disabled:opacity-40 disabled:pointer-events-none transition-colors`;
    prevBtn.innerHTML = '<i data-lucide="chevron-left" class="w-4 h-4"></i>';
    prevBtn.disabled = currentPage === 1;
    prevBtn.title = "Página Anterior";
    prevBtn.addEventListener('click', () => {
        if (state.page > 1) {
            state.page--;
            loadBooks();
        }
    });
    controlsEl.appendChild(prevBtn);

    // Jump to page input
    const pageBadge = document.createElement('span');
    pageBadge.className = 'text-xs font-mono font-bold text-purple-300 px-3 py-1 rounded-lg bg-purple-950/60 border border-purple-800/50';
    pageBadge.textContent = `${currentPage} / ${totalPages}`;
    controlsEl.appendChild(pageBadge);

    // Next button
    const nextBtn = document.createElement('button');
    nextBtn.className = `p-2 rounded-xl bg-[#0d1326] border border-slate-800 text-slate-400 hover:text-white disabled:opacity-40 disabled:pointer-events-none transition-colors`;
    nextBtn.innerHTML = '<i data-lucide="chevron-right" class="w-4 h-4"></i>';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.title = "Próxima Página";
    nextBtn.addEventListener('click', () => {
        if (state.page < totalPages) {
            state.page++;
            loadBooks();
        }
    });
    controlsEl.appendChild(nextBtn);

    lucide.createIcons();
}

function openReader(book) {
    state.activeBook = book;
    document.getElementById('readerBookTitle').textContent = book.title;
    document.getElementById('readerBookAuthor').textContent = `${book.author} (${book.year})`;
    
    if (book.format === 'epub') {
        openEpubViewer(book.id, book.epub_cfi);
    } else {
        openPdfViewer(book.id, book.current_page || 1);
    }
}

function closeReader() {
    document.getElementById('readerModal').classList.add('hidden');
    state.activeBook = null;
    loadStats();
    loadBooks();
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => console.log(err));
    } else {
        if (document.exitFullscreen) document.exitFullscreen();
    }
}

function openEditModal(book) {
    state.editingBook = book;
    document.getElementById('editBookId').value = book.id;
    document.getElementById('editTitleInput').value = book.title;
    document.getElementById('editAuthorInput').value = book.author;
    document.getElementById('editYearInput').value = book.year === 'XXXX' ? '' : book.year;
    document.getElementById('editFilenamePreview').textContent = book.filename;
    
    document.getElementById('editModal').classList.remove('hidden');
    document.getElementById('editTitleInput').focus();
}

async function handleEditSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('editBookId').value;
    const title = document.getElementById('editTitleInput').value.trim();
    const author = document.getElementById('editAuthorInput').value.trim();
    const year = document.getElementById('editYearInput').value.trim() || 'XXXX';

    try {
        const res = await fetch(`/api/books/${id}/metadata`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, author, year })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Erro ao atualizar');
        }

        showToast('Metadados e arquivo renomeados com sucesso!');
        document.getElementById('editModal').classList.add('hidden');
        loadBooks();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function openMoveModal(book) {
    state.movingBook = book;
    state.isCreatingNewCategory = false;
    state.isCreatingNewLanguage = false;
    
    document.getElementById('moveBookId').value = book.id;
    
    const catSelect = document.getElementById('moveCategorySelect');
    const newCatInput = document.getElementById('newCategoryInput');
    const toggleCatBtn = document.getElementById('toggleNewCategoryBtn');
    
    const langSelect = document.getElementById('moveLanguageSelect');
    const newLangInput = document.getElementById('newLanguageInput');
    const toggleLangBtn = document.getElementById('toggleNewLanguageBtn');
    
    catSelect.classList.remove('hidden');
    if (newCatInput) newCatInput.classList.add('hidden');
    if (toggleCatBtn) toggleCatBtn.textContent = '+ Criar Nova';
    
    langSelect.classList.remove('hidden');
    if (newLangInput) newLangInput.classList.add('hidden');
    if (toggleLangBtn) toggleLangBtn.textContent = '+ Criar Novo';
    
    catSelect.value = book.category;
    langSelect.value = book.language || 'Portugues';
    
    document.getElementById('movePathPreview').textContent = `Books/${book.category}/${book.language}/${book.filename}`;
    document.getElementById('moveModal').classList.remove('hidden');
}

async function handleMoveSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('moveBookId').value;
    
    const catSelect = document.getElementById('moveCategorySelect');
    const newCatInput = document.getElementById('newCategoryInput');
    const category = state.isCreatingNewCategory ? (newCatInput.value.trim()) : catSelect.value;
    
    const langSelect = document.getElementById('moveLanguageSelect');
    const newLangInput = document.getElementById('newLanguageInput');
    const language = state.isCreatingNewLanguage ? (newLangInput.value.trim()) : langSelect.value;

    if (!category || !language) {
        showToast('Categoria e idioma são obrigatórios.', 'error');
        return;
    }

    try {
        const res = await fetch(`/api/books/${id}/move`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, language })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Erro ao mover arquivo');
        }

        showToast('Livro movido com sucesso!');
        document.getElementById('moveModal').classList.add('hidden');
        await loadStats();
        await loadLanguages();
        await loadBooks();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function toggleFav(bookId) {
    try {
        const res = await fetch(`/api/books/${bookId}/favorite`, { method: 'POST' });
        const book = await res.json();
        showToast(book.is_favorite ? 'Adicionado aos favoritos!' : 'Removido dos favoritos.');
        loadStats();
        loadBooks();
    } catch (e) {
        showToast('Erro ao favoritar: ' + e.message, 'error');
    }
}

async function saveReadingProgress(bookId, currentPage, totalPages, epubCfi = null) {
    try {
        await fetch(`/api/books/${bookId}/progress`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_page: currentPage,
                total_pages: totalPages,
                epub_cfi: epubCfi
            })
        });
    } catch (e) {
        console.error('Error saving progress:', e);
    }
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'border-rose-700 text-rose-200' : 'border-purple-700 text-purple-200'}`;
    toast.innerHTML = `
        <i data-lucide="${type === 'error' ? 'alert-circle' : 'check-circle'}" class="w-4 h-4 shrink-0"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

async function resetBookProgress(bookId, bookTitle = 'Livro') {
    try {
        const res = await fetch(`/api/books/${bookId}/reset-progress`, { method: 'POST' });
        if (res.ok) {
            showToast(`"${bookTitle}" removido de Continuar Lendo`);
            await loadStats();
            await loadBooks();
        } else {
            showToast('Erro ao remover livro', 'error');
        }
    } catch (e) {
        showToast('Erro na requisição: ' + e.message, 'error');
    }
}
