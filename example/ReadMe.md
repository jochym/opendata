# Thermal conductivity of the 3C-SiC project

> This project is a pilot for the OpenData program.

---

## Folders scheme

- **paper** text of the paper
  - **figures** sub-folder for the generation of final figures
- **analysis** notebooks and other scripts/programs for the analysis of data
- **data** folders for calculation results (raw computational and experimental data)

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
