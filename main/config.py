from typing import Callable, Optional

from rich.console import Console
from rich.style import Style

from lang import translator
from scripts.commands import commands

console = Console(width=100)
title_style = Style(color="white", bold=True)
error_style = Style(color="red", bold=True)
option_style = Style(color="white", bold=True)


class Configuration:
    """Menú de configuración del sistema (idioma, reinstalación de paquetes e info del creador)."""

    def __init__(self, on_exit: Optional[Callable[[], None]] = None):
        self.on_exit = on_exit

    def change_language_flow(self) -> None:
        """Flujo interactivo para cambiar el idioma del sistema."""
        console.print("\n" + translator.t("config.language") + ":\n", style=title_style, justify="full")
        console.print("1 " + translator.t("language.es"), style=option_style, justify="full")
        console.print("2 " + translator.t("language.en"), style=option_style, justify="full")
        console.print(translator.t("config.language.prompt") + " ", style=title_style, end="")

        try:
            lang_option = input().strip()
        except (EOFError, KeyboardInterrupt):
            return

        if lang_option in ("1", "es", "ES"):
            translator.set_language("es")
            commands.clearScreen()
            console.print(translator.t("language.changed"), style=title_style, justify="full")
        elif lang_option in ("2", "en", "EN"):
            translator.set_language("en")
            commands.clearScreen()
            console.print(translator.t("language.changed"), style=title_style, justify="full")
        else:
            console.print(translator.t("language.invalid") + "\n", style=error_style)

    def optionsMenu(self) -> None:
        """Bucle principal de opciones de configuración sin recursión."""
        while True:
            console.print("\n" + translator.t("config.menu.title") + "\n", style=title_style, justify="full")
            console.print("1 " + translator.t("config.option_1"), style=option_style, justify="full")
            console.print("2 " + translator.t("config.option_2"), style=option_style, justify="full")
            console.print("3 " + translator.t("config.option_3"), style=option_style, justify="full")
            console.print("4 " + translator.t("config.option_4") + "\n", style=option_style, justify="full")

            try:
                options = input().strip()
            except (EOFError, KeyboardInterrupt):
                break

            if options == "1":
                self.change_language_flow()
            elif options == "2":
                commands.clearScreen()
                console.print(translator.t("config.reinstalling") + "\n", style=title_style)
                commands.installPackages()
            elif options == "3":
                console.print("\n" + translator.t("config.creator.info") + "\n", style=title_style, justify="full")
            elif options == "4" or options.lower() in ("q", "salir", "exit"):
                commands.clearScreen()
                if self.on_exit is not None:
                    self.on_exit()
                break
            else:
                console.print(translator.t("menu.invalid") + "\n", style=error_style)