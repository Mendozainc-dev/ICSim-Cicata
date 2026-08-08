# ICSim-Cicata
Virtualized environment for fuzzing vulnerability assessment in vehicle internet communication protocols


### Architecture

**If you need to view the architecture for the project, you need to use this comand**

```
tree -L2
```
>use -L2 because this project downloads more stuff, and if you don't use this exception the structure will look bigger

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