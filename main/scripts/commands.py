import subprocess


class Commands:
    def __init__(self):
        pass

    def clearScreen(self):
        subprocess.run("clear", shell=True, check=False)

    def packageVersions(self):
        subprocess.run("python --version", shell=True, check=False)
        subprocess.run("pip --version", shell=True, check=False)
        subprocess.run("curl --version", shell=True, check=False)

    def installPackages(self):
        subprocess.run("pip3 install -r requirements.txt", shell=True, check=False)
        subprocess.run("sudo apt-get install libsdl2-dev libsdl2-image-dev can-utils", shell=True, check=False)
        subprocess.run("cd.. && cd ICSim && meson setup builddir && cd builddir", shell=True, check=False)
        subprocess.run("meson compile", shell=True, check=False)


commands = Commands()
