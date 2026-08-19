from scripts.commands import commands
from rich.console import Console
from rich.style import Style
from lang import translator

console = Console(width=100)
tittle = Style(color="white", bold=True)
error = Style(color="red", blink=True, bold=True)


class Configuration:
    def __init__(self, on_exit=None):
        self.on_exit = on_exit

    def optionsMenu(self):
        console.print("\n" + translator.t("config.menu.title") + "\n", style=tittle, justify="full")

        console.print("\n1 " + translator.t("config.option_1"), style=tittle, justify="full")
        console.print("2 " + translator.t("config.option_2"), style=tittle, justify="full")
        console.print("3 " + translator.t("config.option_3"), style=tittle, justify="full")
        console.print("4 " + translator.t("config.option_4") + "\n", style=tittle, justify="full")

        options = input()

        if options == "1":
            console.print("\n" + translator.t("config.language") + ":\n", style=tittle, justify="full")
            console.print("1 " + translator.t("language.es"), style=tittle, justify="full")
            console.print("2 " + translator.t("language.en"), style=tittle, justify="full")
            lang_option = input().strip()

            if lang_option == "1":
                translator.set_language("es")
                commands.clearScreen()
                console.print(translator.t("language.changed"), style=tittle, justify="full")
                self.optionsMenu()
            elif lang_option == "2":
                translator.set_language("en")
                commands.clearScreen()
                console.print(translator.t("language.changed"), style=tittle, justify="full")
                self.optionsMenu()
            else:
                console.log(translator.t("language.invalid") + "\n", style=error, justify="full")
                self.optionsMenu()
        elif options == "2":
            commands.clearScreen()
            console.log(translator.t("config.reinstalling") + "\n", style=error, justify="full")
            commands.installPackages()
        elif options == "3":
            console.print("\n" + translator.t("config.creator.info") + "\n", style=tittle, justify="full")
            self.optionsMenu()
        elif options == "4":
            commands.clearScreen()
            if self.on_exit is not None:
                self.on_exit()
            return