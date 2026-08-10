#*In this project, a virtualized environment is created to evaluate vulnerabilities through fuzzing in communication protocols of vehicles. The system generates test cases to detect potential vulnerabilities in the communication protocols used by vehicles. and the results of the evaluation are analyzed and reported to improve the security of vehicle communication systems.

# Programer: Mendozainc-dev, working for the asociation cicata (centro de investigacion en computacion aplicada y tecnologia avanzada) queretaro, mexico.

from rich.console import Console
from rich.style import Style
from rich.table import Table

console = Console(width=100)

# Variable to indicate styles
tittle = Style(color="white", bold=True) 
error = Style(color="red", blink=True, bold=True) 
# note: In this style (error), you can change the blink parameter to false if you want to disable the blinking effect for error messages.


# This function is used to display the main menu of the project, it shows a brief description of the project and the options available for the user to select
def Main():

    table = Table(title="\n", show_header=True, header_style="bold white", border_style="white")

    table.add_column("Entorno virtualizado para la evaluacion de vulnerabilidades mediante fuzzing en protocolos de comunicacion de internet de los vehiculos", justify="full", style=tittle, no_wrap=False)

    table.add_row("Este proyecto tiene como objetivo la evaluacion de vulnerabilidades mediante fuzzing en protocolos de comunicacion de internet de los vehiculos, utilizando un entorno virtualizado para simular el comportamiento de los vehiculos y sus sistemas de comunicacion. El sistema de evaluacion se basa en la generacion automatica de casos de prueba para detectar posibles vulnerabilidades en los protocolos de comunicacion utilizados por los vehiculos.")

    console.print(table, justify="center")

    console.print("\nSeleccione una opcion del menu:\n", style=tittle, justify="full")
    menu = Menu()

# This function is used to display the menu options, later the user can select an option to execute a specific function
def Menu():

    styleOptions = Style(color="white", bold=True)

    console.print("1 Informacion del proyecto", style=styleOptions)
    console.print("2 Inicio del sistema de evaluacion de vulnerabilidades mediante fuzzing", style=styleOptions)
    console.print("3 Analisis de resultados y reportes de vulnerabilidades detectadas\n", style=styleOptions)
    optionSelected()

def optionSelected():
    opciones = input()
    if opciones == "1":
        console.print("\nInformacion del proyecto:\n", style=tittle, justify="full")
    elif opciones == "2":
        console.print("\nInicio del sistema de evaluacion de vulnerabilidades mediante fuzzing:\n", style=tittle, justify="full")
    elif opciones == "3":
        console.print("\nAnalisis de resultados y reportes de vulnerabilidades detectadas:\n", style=tittle, justify="full")
    else:
        console.log("Opcion no valida, por favor seleccione una opcion del menu\n", style=error)
        Menu()

Main()