# ETL for UN IGME Child Mortality Estimates

## Data Source

Download the data from the UN IGME website:
https://childmortality.org/all-cause-mortality/data/download

1. Download the ZIP file containing all data
2. Extract the CSV file to `etl/source/UN IGME 2024.csv`

## Setup

```bash
cd etl
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run ETL

```bash
cd etl/scripts
python etl.py
```

This will generate DDF files in the repository root directory.
