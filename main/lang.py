import json
from pathlib import Path
from typing import Any, Dict, Optional


class Translator:
    """Gestor de internacionalización con patrón Singleton para el proyecto."""

    _instance: Optional["Translator"] = None

    def __new__(cls, lang: str = "es") -> "Translator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._texts = {}
        return cls._instance

    def __init__(self, lang: str = "es") -> None:
        if not getattr(self, "_initialized", False):
            self.current_lang = lang
            self._load_language(lang)
            self._initialized = True

    def _load_language(self, lang: str) -> None:
        i18n_dir = Path(__file__).resolve().parent / "i18n"
        file_path = i18n_dir / f"{lang}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"No existe el archivo de idioma: {file_path}")

        with file_path.open("r", encoding="utf-8") as file:
            self._texts: Dict[str, str] = json.load(file)

    def set_language(self, lang: str) -> None:
        self.current_lang = lang
        self._load_language(lang)

    def t(self, key: str, **kwargs: Any) -> str:
        text = self._texts.get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text


translator = Translator()
