import subprocess

class Commands:
    def __init__(self):
        self.start_simulators()

    def clearScreen(self):
        subprocess.run("clear", shell=True)

    def packageVersions(self):
        subprocess.run("python --version", shell=True)

        subprocess.run("pip --version", shell=True)

        subprocess.run("curl --version", shell=True)

    def installPackages(self):
        subprocess.run("pip3 install -r requirements.txt", shell=True)
        subprocess.run("sudo apt-get install libsdl2-dev libsdl2-image-dev can-utils", shell=True)
        subprocess.run("cd.. && cd ICSim && meson setup builddir && cd builddir", shell=True)
        subprocess.run("meson compile", shell=True)

commands = Commands()
    
    def start_simulators(self):
        subprocess.Popen(['gnome-terminal', '--', './icsim', 'vcan0'])
        subprocess.Popen(['gnome-terminal', '--', './controls', 'vcan0'])
