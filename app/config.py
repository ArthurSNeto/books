import json
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
DEFAULT_BOOKS_DIR = BASE_DIR / "Books"

def get_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Fallback to default Books directory if it exists
    default_path = str(DEFAULT_BOOKS_DIR.resolve()) if DEFAULT_BOOKS_DIR.exists() else ""
    return {
        "library_path": default_path,
        "app_name": "Biblioteca Digital PRO",
        "theme": "dark"
    }

def save_config(config_data: dict) -> bool:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_library_dir() -> Optional[Path]:
    config = get_config()
    path_str = config.get("library_path", "").strip()
    if path_str:
        p = Path(path_str)
        if p.exists() and p.is_dir():
            return p
    
    # Default fallback
    if DEFAULT_BOOKS_DIR.exists():
        return DEFAULT_BOOKS_DIR
    
    return None

def set_library_dir(new_path: str) -> tuple[bool, str]:
    p = Path(new_path.strip())
    if not p.exists():
        return False, f"O diretório '{new_path}' não foi encontrado."
    if not p.is_dir():
        return False, f"O caminho '{new_path}' não é um diretório válido."
    
    config = get_config()
    config["library_path"] = str(p.resolve())
    if save_config(config):
        return True, str(p.resolve())
    return False, "Erro ao salvar arquivo de configuração."

def is_library_configured() -> bool:
    lib_dir = get_library_dir()
    return lib_dir is not None and lib_dir.exists()