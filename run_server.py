import uvicorn
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.5)
    print("Opening browser at http://localhost:8000 ...")
    try:
        webbrowser.open("http://localhost:8000")
    except:
        pass

if __name__ == '__main__':
    print("=" * 60)
    print("  Iniciando Servidor da Biblioteca Digital")
    print("  Acesse no navegador: http://localhost:8000")
    print("=" * 60)
    
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
