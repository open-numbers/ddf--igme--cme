# -*- coding: utf-8 -*-
"""Transform Child Mortality Estimates (2024) into DDF model.

Source: https://childmortality.org/all-cause-mortality/data/download
Uses UN IGME 2024 CSV data in long format.
"""

import os
import polars as pl
from ddf_utils.io import dump_json
from ddf_utils.package import get_datapackage
from ddf_utils.str import to_concept_id, format_float_sigfig

# configuration of file paths
source_path = "../source/"
source_name = "UN IGME 2024.csv"
out_dir = "../../"

# Mapping from source indicator names to concept base names
INDICATOR_MAPPING = {
    # Core mortality rates
    "Under-five mortality rate": "u5mr",
    "Infant mortality rate": "imr",
    "Neonatal mortality rate": "nmr",
    "Child Mortality rate age 1-4": "cmr",
    "Mortality rate 1-59 months": "mr_1_59_months",
    "Mortality rate age 1-11 months": "mr_1_11_months",
    "Mortality rate age 5-9": "mr_5_9",
    "Mortality rate age 10-14": "mr_10_14",
    "Mortality rate age 5-14": "mr_5_14",
    "Mortality rate age 15-19": "mr_15_19",
    "Mortality rate age 10-19": "mr_10_19",
    "Mortality rate age 20-24": "mr_20_24",
    "Mortality rate age 15-24": "mr_15_24",
    "Mortality rate age 5-24": "mr_5_24",
    "Stillbirth rate": "stillbirth_rate",
    # Deaths counts
    "Under-five deaths": "under_five_deaths",
    "Infant deaths": "infant_deaths",
    "Neonatal deaths": "neonatal_deaths",
    "Child deaths age 1 to 4": "child_deaths_1_4years",
    "Deaths age 1-59 months": "deaths_1_59_months",
    "Deaths age 1-11 months": "deaths_1_11_months",
    "Deaths age 5 to 9": "deaths_5_9",
    "Deaths age 10 to 14": "deaths_10_14",
    "Deaths age 5 to 14": "deaths_5_14",
    "Deaths age 15 to 19": "deaths_15_19",
    "Deaths age 10 to 19": "deaths_10_19",
    "Deaths age 20 to 24": "deaths_20_24",
    "Deaths age 15 to 24": "deaths_15_24",
    "Deaths age 5 to 24": "deaths_5_24",
    "Stillbirths": "stillbirths",
}

# Mapping from Regional group to entity set
ENTITY_SET_MAPPING = {
    "": "country",
    "UNICEF": "unicef_region",
    "UNSDG": "unsdg_region",
    "WB": "wb_group",
    "WORLD": "world",
}


def load_source_data(source_path: str, source_name: str) -> pl.LazyFrame:
    """Load and filter source CSV for UN IGME estimates."""
    return (
        pl.scan_csv(os.path.join(source_path, source_name))
        .filter(pl.col("Series Name") == "UN IGME estimate")
        .filter(pl.col("Sex") == "Total")
        .filter(pl.col("Wealth Quintile") == "Total")
    )


def extract_concepts_continuous(indicators: list[str]) -> pl.DataFrame:
    """Extract continuous concepts from the indicators list."""
    concepts = []
    for indicator in indicators:
        base_name = INDICATOR_MAPPING.get(indicator, to_concept_id(indicator))
        for suffix in ["lower", "median", "upper"]:
            concept_id = f"{base_name}_{suffix}"
            name = f"{indicator} ({suffix.title()})"
            concepts.append({"concept": concept_id, "name": name, "concept_type": "measure"})
    return pl.DataFrame(concepts)


def extract_concepts_discrete() -> pl.DataFrame:
    """Extract discrete concepts."""
    return pl.DataFrame(
        [
            {
                "concept": "geo",
                "name": "Geographic Location",
                "concept_type": "entity_domain",
                "domain": None,
            },
            {
                "concept": "country",
                "name": "Country",
                "concept_type": "entity_set",
                "domain": "geo",
            },
            {
                "concept": "unicef_region",
                "name": "UNICEF Region",
                "concept_type": "entity_set",
                "domain": "geo",
            },
            {
                "concept": "unsdg_region",
                "name": "UN SDG Region",
                "concept_type": "entity_set",
                "domain": "geo",
            },
            {
                "concept": "wb_group",
                "name": "World Bank Group",
                "concept_type": "entity_set",
                "domain": "geo",
            },
            {
                "concept": "world",
                "name": "World",
                "concept_type": "entity_set",
                "domain": "geo",
            },
            {
                "concept": "name",
                "name": "Name",
                "concept_type": "string",
                "domain": None,
            },
            {
                "concept": "domain",
                "name": "Domain",
                "concept_type": "string",
                "domain": None,
            },
            {
                "concept": "year",
                "name": "Year",
                "concept_type": "time",
                "domain": None,
            },
        ]
    )


def extract_entities_geo(data: pl.LazyFrame) -> pl.DataFrame:
    """Extract geo entities from source data with entity set flags."""
    entities = (
        data.select(
            [
                pl.col("REF_AREA").str.to_lowercase().alias("geo"),
                pl.col("Geographic area").alias("name"),
                pl.col("Regional group").fill_null("").alias("regional_group"),
            ]
        )
        .unique()
        .collect()
        .sort("geo")
    )

    # Add entity set flag columns (uppercase TRUE/FALSE)
    for regional_group, entity_set in ENTITY_SET_MAPPING.items():
        entities = entities.with_columns(
            pl.when(pl.col("regional_group") == regional_group)
            .then(pl.lit("TRUE"))
            .otherwise(pl.lit("FALSE"))
            .alias(f"is--{entity_set}")
        )

    # Drop the temporary regional_group column
    entities = entities.drop("regional_group")

    return entities


def extract_datapoints(data: pl.LazyFrame, indicators: list[str]) -> dict[str, pl.DataFrame]:
    """Extract datapoints for each concept by geo and year."""
    result = {}

    for indicator in indicators:
        base_name = INDICATOR_MAPPING.get(indicator, to_concept_id(indicator))
        print(f"Processing indicator: {indicator} -> {base_name}")

        indicator_data = (
            data.filter(pl.col("Indicator") == indicator)
            .select(
                [
                    pl.col("REF_AREA").str.to_lowercase().alias("geo"),
                    pl.col("Reference Date").ceil().cast(pl.Int64).alias("year"),
                    pl.col("Observation Value").alias("median"),
                    pl.col("Lower Bound").alias("lower"),
                    pl.col("Upper Bound").alias("upper"),
                ]
            )
            .collect()
        )

        # Create separate dataframes for lower, median, upper
        for bound in ["lower", "median", "upper"]:
            concept_id = f"{base_name}_{bound}"
            df = (
                indicator_data.select(["geo", "year", bound])
                .rename({bound: concept_id})
                .drop_nulls(concept_id)
                .sort(["geo", "year"])
            )
            if len(df) > 0:
                result[concept_id] = df

    return result


def main():
    print("Reading source file...")
    data = load_source_data(source_path, source_name)

    # Get list of available indicators
    available_indicators = data.select("Indicator").unique().collect().to_series().to_list()

    # Filter to only indicators we have mappings for
    indicators = [i for i in available_indicators if i in INDICATOR_MAPPING]
    print(f"Found {len(indicators)} indicators: {indicators}")

    print("Extracting concept files...")
    continuous = extract_concepts_continuous(indicators)
    path = os.path.join(out_dir, "ddf--concepts--continuous.csv")
    continuous.write_csv(path)

    discrete = extract_concepts_discrete()
    path = os.path.join(out_dir, "ddf--concepts--discrete.csv")
    discrete.write_csv(path)

    print("Extracting entities files...")
    entities = extract_entities_geo(data)
    path = os.path.join(out_dir, "ddf--entities--geo.csv")
    entities.write_csv(path)

    print("Extracting data points...")
    datapoints = extract_datapoints(data, indicators)
    for concept_id, df in datapoints.items():
        path = os.path.join(out_dir, f"ddf--datapoints--{concept_id}--by--geo--year.csv")
        # Format floats with significant figures
        df = df.with_columns(
            pl.col(concept_id).map_elements(
                lambda x: format_float_sigfig(x) if x is not None else None,
                return_dtype=pl.String,
            )
        )
        df.write_csv(path)
        print(f"  Wrote {len(df)} rows to {concept_id}")

    # print("Generating datapackage.json...")
    # dps = get_datapackage(out_dir, update=True)
    # dump_json(os.path.join(out_dir, "datapackage.json"), dps)

    print("Done!")


if __name__ == "__main__":
    main()
