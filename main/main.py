from rich.console import Console
from rich.style import Style
from rich.table import Table

console = Console(width=100)

# Variable to indicate styles
tittle = Style(color="white", bold=True) #Title style in color white and bold, changue the value of color to change the color of the title if you want
error = Style(color="red", blink=True, bold=True) #Error style in color red, blink and bold, changue the value of color to change the color of the error if you want, only used in logs (console.log)


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

    console.print("1.Informacion del proyecto", style=styleOptions)
    console.print("2.Inicio del sistema de evaluacion de vulnerabilidades mediante fuzzing", style=styleOptions)
    console.print("3.Analisis de resultados y reportes de vulnerabilidades detectadas\n", style=styleOptions)

Main()