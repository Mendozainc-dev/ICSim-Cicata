# In this project, a virtualized environment is created to evaluate vulnerabilities through fuzzing in communication protocols of vehicles. The system generates test cases to detect potential vulnerabilities in the communication protocols used by vehicles. and the results of the evaluation are analyzed and reported to improve the security of vehicle communication systems.

# Programer: Mendozainc-dev, working for the asociation cicata (centro de investigacion en computacion aplicada y tecnologia avanzada) queretaro, mexico.

import sys


from scripts.scripts_menu import menu_script
from scripts.commands import commands
from config import Configuration
from rich.console import Console
from rich.style import Style
from rich.table import Table
from lang import translator



console = Console(width=100)

# Variable to indicate styles
tittle = Style(color="white", bold=True)
error = Style(color="red", blink=True, bold=True)
# note: In this style (error), you can change the blink parameter to false if you want to disable the blinking effect for error messages.


# This function is used to display the main menu of the project, it shows a brief description of the project and the options available for the user to select
def Main():

    commands.clearScreen()

    table = Table(title="\n", show_header=True, header_style="bold white", border_style="white")

    table.add_column(translator.t("project.title"), justify="full", style=tittle, no_wrap=False)

    table.add_row(translator.t("project.description"))

    console.print(table, justify="center")
    menu = Menu()

def showProjectInfo():
    commands.clearScreen()

    info = "\n\n".join([
        translator.t("project.description"),
        translator.t("info.goal.description"),
        translator.t("info.environment.description"),
        translator.t("info.components.description"),
        translator.t("info.usage.description"),
        translator.t("info.author.description"),
    ])

    table = Table(title="\n", show_header=True, header_style="bold white", border_style="white")
    table.add_column(translator.t("project.title"), justify="full", style=tittle, no_wrap=False)
    table.add_row(info)
    console.print(table, justify="center")

    console.print("\n" + translator.t("info.back") + "\n", style=tittle, justify="center")
    input()
    commands.clearScreen()
    Main()


# This function is used to display the menu options, later the user can select an option to execute a specific function
def Menu():

    styleOptions = Style(color="white", bold=True)

    console.print("\n" + translator.t("menu.title") + ":", style=tittle, justify="full")
    console.print("\n1 " + translator.t("menu.option_1"), style=styleOptions)
    console.print("2 " + translator.t("menu.option_2"), style=styleOptions)
    console.print("3 " + translator.t("menu.option_3"), style=styleOptions)
    console.print("4 " + translator.t("menu.option_4"), style=styleOptions)
    console.print("5 " + translator.t("menu.option_5"), style=styleOptions)
    console.print("6 " + translator.t("menu.option_6") + "\n", style=styleOptions)
    optionSelected()


def optionSelected():
    opciones = input().strip()
    if opciones == "1":
        showProjectInfo()
    elif opciones == "2":
        commands.clearScreen()
        commands.start_simulators()
        menu_script()
    elif opciones == "3":
        console.print("\n" + translator.t("project.analysis") + "\n", style=tittle, justify="full")
    elif opciones == "4":
        console.print("\n" + translator.t("project.versions") + "\n", style=tittle, justify="full")
        commands.clearScreen()
        commands.packageVersions()
        Menu()
    elif opciones == "5":
        console.print("\n" + translator.t("project.config") + "\n", style=tittle, justify="full")
        commands.clearScreen()
        configuration = Configuration(on_exit=Main)
        configuration.optionsMenu()
    elif opciones == "6":
        commands.clearScreen()
        console.print("\n" + translator.t("project.exit") + "\n", style=tittle, justify="center")
        sys.exit(0)
    else:
        console.log(translator.t("menu.invalid") + "\n", style=error)
        Menu()

Main()
