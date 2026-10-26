# TR10/lib.tech/klayout Directory Structure 
```
klayout -- README.md
        +- d25
        +- drc
        +- lvs
        +- macros
        +- pymacros
        +- python --- cells
        +- ruby
        +- tech   --- TR10.lyp
        +- klayoutrc  
```

## Contents
|         | Description |
| ------- | ---------   |
|- **d25**       | directory contain 2.5D (empty).
|- **drc**       | directory contain DRC runset files.
|- **lvs**       | directory contain LVS runset files.
|- **macros**    | directory contain MACRO files (empty).
|- **pymacro**   | directory contain Python macro files.
|- **python**    | directory contain Python.py files.
|- **ruby**      | directory contain Ruby related (empty).
|- **tech**      | directory contain TR10.lyp Layer files.
|- **klayoutrc** | Klayout resource file.

# Usage

You have three options for installing this package:

Option: git clone git@github.com:OpenSUSI/TR10.git
From inside the repository run this command to start KLayout in edit mode:

KLAYOUT_PATH=. klayout -e

Option: ln -s $PWD/TR10/lib.tech/klayout $HOME/.klayout

klayout -e

# License
If not otherwise noted The Apache License, version 2.0.
