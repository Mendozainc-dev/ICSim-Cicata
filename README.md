# ICSim-Cicata
Virtualized environment for fuzzing vulnerability assessment in vehicle internet communication protocols

### Requeriments
To install this project you need to have these packages on your PC

* ```python``` **The language for executing the project**

* ```pip``` **Python package management**

* ```curl``` **Package for the instalation this project** 


>If you don't have these packages, you can use the command below

```
sudo apt install python
sudo apt install pip
sudo apt install curl
```
>On Windows OS you need to install Python from https://www.python.org/downloads/

### How to install

Installation is very simple with this command, you can use it to install and use

```
curl -fsSL https://raw.githubusercontent.com/Mendozainc-dev/ICSim-Cicata/main/install.sh | bash
```

>Your first question is, where is my project? This command is program, to install all the files in a single directory, and where is the directory, this directory is always in the home folder, so Just look in the Home folder

### Architecture

**If you need to view the architecture for the project, you need to use this comand**

```
tree -L2
```
>Use ```-L2``` because this project downloads more stuff, and if you don't use this exception the structure will look bigger

```
├── ICSim 
│   ├── art
│   ├── controls.c
│   ├── data
│   ├── icsim.c
│   ├── lib.c
│   ├── lib.h
│   ├── lib.o
│   ├── LICENSE
│   ├── Makefile
│   ├── meson.build
│   ├── README.md
│   └── setup_vcan.sh
├── LICENSE
├── main
│   ├── main.py
│   ├── modules
│   ├── requirements.txt
│   └── venv
└── README.md
```