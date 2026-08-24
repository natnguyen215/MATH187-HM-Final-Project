# Optimal Degree Path Planning

This repository contains a **class project** created in 2025 by Nathan Nguyen, Cole Plepel, and Joshua Zhong. It explores four-year course planning at Harvey Mudd College as a mixed-integer optimization problem.

The model balances graduation and major requirements, prerequisites, course availability, student interests, and semester credit loads. It was built as an academic case study and is not an official advising or degree-audit tool.

## Repository structure

- `src/` — Python scripts for collecting and transforming course data
- `model/` — the MathProg/AMPL-style optimization model
- `data/catalog/` — course catalog snapshots used by the project
- `data/requirements/` — department and graduation requirement inputs
- `data/generated/` — generated model data retained for reproducibility
- `examples/` — sample student-interest inputs
- `report/` — LaTeX source and tables for the final class report

## Using the project

The data-processing scripts require Python 3. The course scraper additionally uses Selenium and `webdriver-manager`:

```bash
python -m pip install -r requirements.txt
```

Each script prints its expected command-line arguments when run without enough inputs. The optimization model requires a solver that supports GNU MathProg/AMPL-style models, such as GLPK.

The final report can be built by running a LaTeX compiler from the `report/` directory:

```bash
pdflatex main.tex
```

## Notes

- Course data reflects the snapshots used for the class project and may now be outdated.
- Generated schedules should be checked against the current college catalog and an academic advisor.
- No license has been added; the work remains with its original authors.

