============================================================
OMOP CLINICAL + WAVEFORM EXPLORER
FIRST INSTALLATION GUIDE
========================

This file explains how to set up the GUI for the first time and how to run it afterwards.

============================================================
PROJECT FOLDER
==============

The following files should all be placed in the SAME folder:

* mimic_iv_final.sql
* restore_original_dump.py
* run_omop_explorer.py
* app_new.py
* omop_db.py
* requirements.txt
* README_FIRST_RUN.txt

IMPORTANT:

Keep all files together.

Do not move:

* app_new.py
* omop_db.py
* mimic_iv_final.sql

to different folders.

The scripts automatically look for these files in their own folder.

============================================================
PREREQUISITES
=============

Before using the GUI you need:

1. PostgreSQL installed

Recommended version:

* PostgreSQL 18

Download:

https://www.postgresql.org/download/

---

2. Python installed

Recommended:

* Python 3.11+
* Python 3.12 also works

---

3. Required Python packages

Open a terminal inside the project folder and run:

pip install -r requirements.txt

============================================================
FIRST TIME SETUP
================

STEP 1

Make sure all project files are inside the same folder.

---

STEP 2

Open:

restore_original_dump.py

and check that the PostgreSQL path is correct:

PG_BIN = r"C:\Program Files\PostgreSQL\18\bin"

If PostgreSQL is installed somewhere else, update this value.

---

STEP 3

Run:

python restore_original_dump.py

This script will:

* create the database mimic_iv_clinical_hosp
* restore the original SQL dump
* prepare the database for the next step

Wait until the restore is completed.

============================================================
STEP 4
======

Run:

python run_omop_explorer.py

This script will:

* check the database
* create the required optimization tables
* create indexes
* create dashboard statistics
* launch Streamlit automatically

The first execution may take a few minutes.

============================================================
USING THE GUI
=============

Once Streamlit starts, open:

http://localhost:8501

Available pages:

* Overview
* Patient Explorer
* Clinical Timeline
* Waveform Analytics
* Medications
* Conditions
* Doctor Notes

============================================================
DAILY USAGE
===========

After the first setup you DO NOT need to restore the database again.

From then on simply run:

python run_omop_explorer.py

and the GUI will start normally.

============================================================
FULL RESET
==========

If you want to rebuild everything from scratch:

Open:

restore_original_dump.py

and change:

DROP_EXISTING_DATABASE = False

to:

DROP_EXISTING_DATABASE = True

Then run:

python restore_original_dump.py

and afterwards:

python run_omop_explorer.py

============================================================
COMMON ISSUES
=============

Error:

Cannot find pg_dump
Cannot find psql
Cannot find createdb

Solution:

Check the value of:

PG_BIN

inside:

* restore_original_dump.py
* run_omop_explorer.py

---

Error:

Database does not exist

Solution:

Run:

python restore_original_dump.py

---

Error:

Streamlit is not installed

Solution:

pip install -r requirements.txt

============================================================
QUICK SUMMARY
=============

First installation:

python restore_original_dump.py

↓

python run_omop_explorer.py

↓

GUI

---

All future executions:

python run_omop_explorer.py

↓

GUI

============================================================
