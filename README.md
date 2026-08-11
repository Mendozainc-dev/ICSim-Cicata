# ICSim-Cicata
Virtualized environment for fuzzing vulnerability assessment in vehicle internet communication protocols

### How to install

Installation is very simple with this command, you can use it to install and use

>Your first question is, where is my project? This command is program, to install all the files in a single directory, and where is the directory, this directory is always in the home folder, so Just look in the Home folder

```
curl -fsSL https://raw.githubusercontent.com/Mendozainc-dev/ICSim-Cicata/main/install.sh | bash
```

### Architecture

**If you need to view the architecture for the project, you need to use this comand**

```
tree -L2
```
>Use -L2 because this project downloads more stuff, and if you don't use this exception the structure will look bigger

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