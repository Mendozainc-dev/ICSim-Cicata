from scripts.script1 import RandomCANFuzzer

from rich.console import Console
from rich.style import Style
from lang import translator

console = Console(width=100)
tittle = Style(color="white", bold=True)
error = Style(color="red", blink=True, bold=True)
styleOptions = Style(color="white", bold=True)


def menu_script():
    console.print("\n" + translator.t("menu.script_title") + ":", style=tittle, justify="full")
    console.print("\n1 " + translator.t("first.script"), style=styleOptions)
    console.print("2 " + translator.t("second.script"), style=styleOptions)
    console.print("3 " + translator.t("third.script") + "\n", style=styleOptions)
    option = input().strip()
    if option == "1":
        fuzzer = RandomCANFuzzer()
        fuzzer.run()
    elif option == "2":
        fuzzer = RandomCANFuzzer()
        fuzzer.run(max_packets=1000)
    elif option == "3":
        fuzzer = RandomCANFuzzer()
        fuzzer.run(max_packets=10000)
    else:
        console.print("\n" + translator.t("menu.invalid_option") + "\n", style=error, justify="full")
        menu_script()
