import subprocess

class Commands:
    def __init__(self):
        pass

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