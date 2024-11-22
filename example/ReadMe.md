# Open Data project

> This project is a pilot for the OpenData program.

---

## Folders scheme

- **paper** text of the paper
  - **figures** sub-folder for the generation of final figures
- **analysis** notebooks and other scripts/programs for the analysis of data
- **data** folders for calculation results (raw computational and experimental data)

## Files in the root directory

- **README.md** this file
- **OpenData.yaml** metadata file in YAML format, it is shaped following the DataVerse metadata used in the RODBUK repository. The further OpenData.yaml files in the `paper` sub-directory is shaped after MyST metadata and can be used directly as a header for the paper if it is written in [MyST](https://mystmd.org/). Here is a short example:

```yaml
title: 
  - Long title of the OpenData project
short_title: 
  - OpenData project
authors:
  - name: First Author
    affiliations:
      - Institute ...
    email: author.one@ifj.edu.pl
    corresponding: true
  - name: Second Author
    affiliations:
      - University ...
bibliography:
  - refs.bib
keywords:
  - OpenData
  - OpenAccess
  - CC-by-SA
```

Each sub-directory should contain similar OpenData.yaml file describing its contents. See the examples in the subdirectories for more elaborated examples.