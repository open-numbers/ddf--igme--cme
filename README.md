# Child Mortality Estimates

DDF dataset containing child mortality estimates from the UN Inter-agency Group for Child Mortality Estimation (UN IGME).

## Source

UN IGME: https://childmortality.org/all-cause-mortality/data/download

## Coverage

### Geographic entities

- Countries
- UNICEF regions
- UN SDG regions
- World Bank income groups
- World aggregate

### Indicators

Mortality rates and death counts with lower, median, and upper uncertainty bounds:

- Under-five mortality rate (U5MR)
- Infant mortality rate (IMR)
- Neonatal mortality rate (NMR)
- Child mortality rate age 1-4 (CMR)
- Mortality rates for ages 5-9, 10-14, 15-19, 20-24, and combined age groups
- Stillbirth rate
- Death counts for all corresponding age groups

### Not included

The source data contains disaggregations by sex (Male/Female) and wealth quintile (Lowest to Highest) which are **not included** in this dataset. Only aggregate totals are extracted.

## ETL

See [etl/README.md](etl/README.md) for instructions on updating the dataset.
