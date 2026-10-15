"""Módulo de compatibilidad para scripts_menu delegando a main.menu."""

from menu.scripts_menu import ScriptsMenu, menu_script

__all__ = ["ScriptsMenu", "menu_script"]

if __name__ == "__main__":
    menu_script()
