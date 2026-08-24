// ePub.js Integration with in-memory Base64 Payload & IDM Bypass
let currentEpubBook = null;
let currentRendition = null;

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
            'body': { 'background': '#090d1a', 'color': '#e2e8f0', 'font-family': 'system-ui, sans-serif' },
            'p': { 'line-height': '1.7' },
            'h1, h2, h3': { 'color': '#c7d2fe' }
        });
        currentRendition.themes.select('dark');
        
        if (startCfi) {
            await currentRendition.display(startCfi);
        } else {
            await currentRendition.display();
        }
        
        currentRendition.on('relocated', function(location) {
            const cfi = location.start.cfi;
            saveReadingProgress(currentBookId, 1, 100, cfi);
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
