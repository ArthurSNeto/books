// PDF.js Integration with in-memory Base64 Payload & IDM Bypass
let currentPdfDoc = null;
let currentPdfPage = 1;
let currentPdfTotalPages = 1;
let pdfScale = 1.2;
let currentBookId = null;
let isDarkMode = true;
let isRendering = false;
let pendingPage = null;

async function openPdfViewer(bookId, startPage = 1) {
    currentBookId = bookId;
    currentPdfPage = startPage || 1;
    
    const modal = document.getElementById('readerModal');
    const loader = document.getElementById('readerLoader');
    const pdfContainer = document.getElementById('pdfContainer');
    const epubContainer = document.getElementById('epubContainer');
    
    modal.classList.remove('hidden');
    loader.classList.remove('hidden');
    pdfContainer.classList.remove('hidden');
    epubContainer.classList.add('hidden');
    
    try {
        // Fetch JSON payload via POST (completely bypasses IDM and download managers)
        const response = await fetch(`/api/books/${bookId}/payload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error(`Erro no servidor (${response.status})`);
        }
        
        const payload = await response.json();
        const base64Data = payload.data;
        
        // Convert base64 to binary Uint8Array in browser memory
        const binaryString = atob(base64Data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        
        const loadingTask = pdfjsLib.getDocument({
            data: bytes
        });
        
        currentPdfDoc = await loadingTask.promise;
        currentPdfTotalPages = currentPdfDoc.numPages;
        
        document.getElementById('readerTotalPages').textContent = currentPdfTotalPages;
        document.getElementById('readerPageInput').max = currentPdfTotalPages;
        
        if (currentPdfPage > currentPdfTotalPages || currentPdfPage < 1) {
            currentPdfPage = 1;
        }
        
        await renderPdfPage(currentPdfPage);
        loader.classList.add('hidden');
    } catch (err) {
        console.error('Error loading PDF in reader:', err);
        alert('Erro ao carregar o livro: ' + err.message);
        loader.classList.add('hidden');
    }
}

async function renderPdfPage(pageNumber) {
    if (isRendering) {
        pendingPage = pageNumber;
        return;
    }
    
    isRendering = true;
    currentPdfPage = pageNumber;
    document.getElementById('readerPageInput').value = pageNumber;
    
    try {
        const page = await currentPdfDoc.getPage(pageNumber);
        const canvas = document.getElementById('pdfCanvas');
        const ctx = canvas.getContext('2d');
        
        const viewport = page.getViewport({ scale: pdfScale });
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        const renderContext = {
            canvasContext: ctx,
            viewport: viewport
        };
        
        await page.render(renderContext).promise;
        isRendering = false;
        
        if (pendingPage !== null) {
            const nextP = pendingPage;
            pendingPage = null;
            await renderPdfPage(nextP);
        } else {
            // Save reading progress to database
            saveReadingProgress(currentBookId, currentPdfPage, currentPdfTotalPages);
        }
    } catch (e) {
        console.error('Render page error:', e);
        isRendering = false;
    }
}

function pdfNextPage() {
    if (currentPdfPage < currentPdfTotalPages) {
        renderPdfPage(currentPdfPage + 1);
    }
}

function pdfPrevPage() {
    if (currentPdfPage > 1) {
        renderPdfPage(currentPdfPage - 1);
    }
}

function pdfZoomIn() {
    pdfScale = Math.min(3.0, pdfScale + 0.2);
    document.getElementById('zoomLevelText').textContent = `${Math.round(pdfScale * 100)}%`;
    renderPdfPage(currentPdfPage);
}

function pdfZoomOut() {
    pdfScale = Math.max(0.5, pdfScale - 0.2);
    document.getElementById('zoomLevelText').textContent = `${Math.round(pdfScale * 100)}%`;
    renderPdfPage(currentPdfPage);
}

function toggleReaderTheme() {
    isDarkMode = !isDarkMode;
    const pdfContainer = document.getElementById('pdfContainer');
    const icon = document.getElementById('themeIcon');
    if (isDarkMode) {
        pdfContainer.classList.add('pdf-dark-mode');
        pdfContainer.classList.remove('pdf-light-mode');
        icon.classList.add('text-purple-400');
    } else {
        pdfContainer.classList.remove('pdf-dark-mode');
        pdfContainer.classList.add('pdf-light-mode');
        icon.classList.remove('text-purple-400');
    }
}
