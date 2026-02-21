# ReadMe for the project
> This project is also used as a pilot for the OpenData program.

---
## $\text{FeSi}_2$ project folders scheme

All project files are located under **Project** directory. In general you should stay within this directory. The sub-directories are:

- **paper** text of the paper
  - **figures** sub-folder for the generation of final figures
- **analysis** notebooks and other scripts/programs for the analysis of data
- **data** folders for calculation results (raw computational and experimental data)

### Compiling the LaTeX file

For automatic, on-line compilation go to the **Project/paper** directory, open new terminal window and execute:
```shell
./watch_and_compile.sh main
```
where `main` should be the name of the main file without `.tex` extension. 
The file will be automatically compiled each time it is saved (similar to Overleaf). The preview will be automatically updated.

To stop the compilation loop press `Ctrl-C` in the terminal.

## Workspaces

Please use your own workspace for your work. Do not work in default workspace.  
This will make each window setup persistent and prevents conflicts while
working simultanously.

## Files in the root directory

- **README.md** this file
- **OpenData.yaml** metadata file in YAML format, it is shaped after MyST metadata and can be used directly as a header for the paper if it is written in [MyST](https://mystmd.org/). Only `authors` and `id` fields are used in the automatic creation of the project access data:

```yaml
title: 
  - Long title of the OpenData project
short_title: 
  - OpenData project
authors:
  - name: First Author
    id: author_1
    affiliations:
      - Institute ...
    corresponding: true
    email: author.one@ifj.edu.pl
  - name: Second Author
    id: author_2
    affiliations:
      - University ...
bibliography:
  - refs.bib
keywords:
  - OpenData
  - OpenAccess
  - CC-by-SA
```
