
from scripts.commands import commands
from rich.console import Console
from rich.style import Style

console = Console(width=100)
tittle = Style(color="white", bold=True) 
error = Style(color="red", blink=True, bold=True)


class Configuration:
    def __init__(self):
        pass

    def optionsMenu(self):

        console.print("\nSeleccione una opcion del menu:\n", style=tittle, justify="full")

        console.print("\n1 Change Language", style=tittle, justify="full")
        console.print("2 Reinstalacion de paquetes", style=tittle, justify="full")
        console.print("3 Informacion del creador", style=tittle, justify="full")
        console.print("4 Salir de configuracion\n", style=tittle, justify="full")

        options = input()

        if options == "1":
            console.print("\nChange Language:\n", style=tittle, justify="full")
            commands.clearScreen()
        elif options == "2":
            commands.clearScreen()
            console.log("Reinstalando paquetes\n", style=error, justify="full")
            commands.installPackages()
