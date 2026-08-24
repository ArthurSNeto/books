// ePub.js Integration with in-memory Base64 Payload & IDM Bypass
let currentEpubBook = null;
let currentRendition = null;
let currentEpubTotalPages = 1;
let currentEpubCurrentPage = 1;

async function openEpubViewer(bookId, startCfi = null) {
    currentBookId = bookId;
    
    const modal = document.getElementById('readerModal');
    const loader = document.getElementById('readerLoader');
    const pdfContainer = document.getElementById('pdfContainer');
    const epubContainer = document.getElementById('epubContainer');
    
    modal.classList.remove('hidden');
    loader.classList.remove('hidden');
    pdfContainer.classList.add('hidden');
    epubContainer.classList.remove('hidden');
    
    try {
        const response = await fetch(`/api/books/${bookId}/payload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error(`Erro ao obter livro (${response.status})`);
        }
        
        const payload = await response.json();
        const binaryString = atob(payload.data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        
        const viewerEl = document.getElementById('epubViewer');
        viewerEl.innerHTML = '';
        
        currentEpubBook = ePub(bytes.buffer);
        currentRendition = currentEpubBook.renderTo('epubViewer', {
            width: '100%',
            height: '100%',
            flow: 'paginated',
            spread: 'auto'
        });
        
        currentRendition.themes.register('dark', {
            'body': { 'background': '#090d1a', 'color': '#e2e8f0', 'font-family': 'system-ui, sans-serif', 'padding': '0 20px' },
            'p': { 'line-height': '1.7', 'margin-bottom': '1em' },
            'h1, h2, h3, h4': { 'color': '#c7d2fe' }
        });
        currentRendition.themes.select('dark');
        
        // Wait for book ready and generate pagination locations
        currentEpubBook.ready.then(async () => {
            const spineCount = (currentEpubBook.spine && currentEpubBook.spine.length) ? currentEpubBook.spine.length : 1;
            currentEpubTotalPages = spineCount;
            document.getElementById('readerTotalPages').textContent = currentEpubTotalPages;
            document.getElementById('readerPageInput').max = currentEpubTotalPages;
            
            try {
                // Generate 1024-character standard page segments
                await currentEpubBook.locations.generate(1024);
                if (currentEpubBook.locations.total) {
                    currentEpubTotalPages = currentEpubBook.locations.total;
                    document.getElementById('readerTotalPages').textContent = currentEpubTotalPages;
                    document.getElementById('readerPageInput').max = currentEpubTotalPages;
                    
                    const loc = currentRendition.currentLocation();
                    const cfi = (loc && loc.start) ? loc.start.cfi : startCfi;
                    let currPage = currentEpubCurrentPage || 1;
                    if (cfi) {
                        const calcPage = currentEpubBook.locations.locationFromCfi(cfi) + 1;
                        if (calcPage && calcPage > 0) currPage = calcPage;
                    }
                    currentEpubCurrentPage = currPage;
                    document.getElementById('readerPageInput').value = currPage;
                    saveReadingProgress(currentBookId, currPage, currentEpubTotalPages, cfi);
                }
            } catch (e) {
                console.log('EPUB locations generation notice:', e);
            }
        });
        
        if (startCfi) {
            await currentRendition.display(startCfi);
        } else {
            await currentRendition.display();
        }
        
        currentRendition.on('relocated', function(location) {
            const cfi = location.start.cfi;
            let pageNum = 1;
            
            if (currentEpubBook.locations && currentEpubBook.locations.total > 0) {
                pageNum = currentEpubBook.locations.locationFromCfi(cfi) + 1;
            } else if (location.start.displayed && location.start.displayed.page > 0) {
                pageNum = location.start.displayed.page;
            } else if (location.start.index !== undefined) {
                pageNum = location.start.index + 1;
            }
            
            currentEpubCurrentPage = Math.max(1, pageNum);
            const total = currentEpubTotalPages || (currentEpubBook.locations ? currentEpubBook.locations.total : 0) || (currentEpubBook.spine ? currentEpubBook.spine.length : 100);
            
            document.getElementById('readerPageInput').value = currentEpubCurrentPage;
            document.getElementById('readerTotalPages').textContent = total;
            
            saveReadingProgress(currentBookId, currentEpubCurrentPage, total, cfi);
        });
        
        loader.classList.add('hidden');
    } catch (err) {
        console.error('Error loading EPUB:', err);
        alert('Erro ao carregar o livro EPUB: ' + err.message);
        loader.classList.add('hidden');
    }
}

function epubNextPage() {
    if (currentRendition) currentRendition.next();
}

function epubPrevPage() {
    if (currentRendition) currentRendition.prev();
}
