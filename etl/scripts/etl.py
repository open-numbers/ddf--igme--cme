# -*- coding: utf-8 -*-
"""transform Child Mortality Estimates set into DDF model"""

import os
import pandas as pd
import numpy as np
from ddf_utils.io import dump_json
from ddf_utils.package import get_datapackage
from ddf_utils.str import to_concept_id, format_float_sigfig

# configuration of file paths
source_path = '../source/'
source_name = 'UNIGME Rates & Deaths_Under5'  # source xlsx name
out_dir = '../../'  # output dir


def extract_concepts_continuous(data):
    """extract continuous concepts from source data"""

    # headers for dataframe and csv exports
    headers_continuous = ['concept', 'name', 'concept_type']

    # get all concepts
    all_ser = data.columns[3:]  # all series name in source file. like "U5MR.1950"

    concepts = []

    for i in all_ser:
        metric = i[:-5]  # remove the year
        for prefix in ['.Lower', '.Median', '.Upper']:  # bounds
            if metric + prefix not in concepts:
                concepts.append(metric + prefix)

    # build the dataframe
    concepts_continuous = pd.DataFrame([], columns=headers_continuous)
    concepts_continuous['name'] = concepts
    concepts_continuous['concept'] = concepts_continuous['name'].apply(to_concept_id)
    concepts_continuous['concept_type'] = 'measure'

    return concepts_continuous


def extract_concepts_discrete(data):
    """extract discrete concepts from source data"""

    # headers for dataframe and csv exports
    headers_discrete = ['concept', 'name', 'concept_type']

    # build dataframe
    concept_discrete = list(data.columns[:2])  # ISO, Country, uncertainty bound
    concept_discrete.append('Name')

    concept_dis_df = pd.DataFrame([], columns=headers_discrete)
    concept_dis_df['name'] = concept_discrete
    concept_dis_df['concept'] = concept_dis_df['name'].apply(to_concept_id)
    concept_dis_df['concept_type'] = ["string", "entity_domain", "string"]

    # adding the year concept
    concept_dis_df = concept_dis_df.append(
        pd.DataFrame([['year', 'Year', 'time']],
                     index=[0], columns=concept_dis_df.columns))

    return concept_dis_df


def extract_entities_country(data):
    """extract country entities from source data"""

    # headers for dataframe and csv exports
    headers_entities = ['iso_code', 'name', 'country']

    # build dataframe
    entities = data[['ISO Code', 'Country']].copy()
    entities['country'] = entities['ISO Code'].apply(to_concept_id)

    entities.columns = headers_entities
    entities = entities.drop_duplicates()

    return entities.loc[:, ::-1]  # move country column at first


def extract_datapoints_country_year(data):
    """extract datapoints for each concept by country and year"""

    # first, construct a dict that contains all metrics as key and a list of
    # columns related to a metric as value of a key.
    # we will later pass the dict to data.loc[: col[key]] to get all data
    # point for a metric.

    metrics = []
    for i in data.columns[3:]:
        s = i[:-5]
        if s not in metrics:
            metrics.append(s)

    print("metrics in the sheet: {}".format(metrics))

    col = {}
    for m in metrics:
        col[m] = list(filter(lambda x: x.startswith(m), data.columns))

    # now we loop through each metrics and create data frame.
    res = {}
    for m in metrics:
        col_metric = np.r_[data.columns[:3], col[m]]
        # change the column form metirc.year to year
        col_metric_new = list(map(lambda x: x[-4:], col[m]))
        col_metric_new = np.r_[data.columns[:3], col_metric_new]

        data_metric = data[col_metric].copy()
        data_metric.columns = col_metric_new

        gs = data_metric.groupby(by='Uncertainty bounds*')

        for p in ['Lower', 'Median', 'Upper']:
            name = to_concept_id(m + '.' + p)
            data_bound = gs.get_group(p)
            data_bound = data_bound.set_index('ISO Code')
            data_bound = (data_bound.drop(['Country', 'Uncertainty bounds*'], axis=1)
                          .unstack().reset_index().dropna())

            # after unstack() the year column will be the first column.
            data_bound.columns = ['year', 'country', name]
            data_bound = data_bound[['country', 'year', name]].sort_values(by=['country', 'year'])
            data_bound['country'] = data_bound['country'].map(to_concept_id)
            res[name] = data_bound
    print(list(res.keys()))
    return res


if __name__ == '__main__':
    print('reading source file...')
    sheets = ['Rates and Deaths U5MR', 'Rates and Deaths IMR', 'Rates and Deaths NMR', 'Rates and Deaths CMR']
    data = list()
    for s in sheets:
        df = pd.read_excel(os.path.join(source_path, source_name + '.xlsx'),
                           skiprows=10, skipfooter=1, sheet_name=s).dropna(how='all', axis=1)
        data.append(df)
    data = pd.concat(data, sort=False)
    # import ipdb; ipdb.set_trace()

    print('extracting concept files...')
    continuous = extract_concepts_continuous(data)
    path = os.path.join(out_dir, 'ddf--concepts--continuous.csv')
    continuous.to_csv(path, index=False)

    discrete = extract_concepts_discrete(data)
    path = os.path.join(out_dir, 'ddf--concepts--discrete.csv')
    discrete.to_csv(path, index=False)

    print('extracting entities files...')
    entities = extract_entities_country(data)
    path = os.path.join(out_dir, 'ddf--entities--country.csv')
    entities.to_csv(path, index=False)

    print('extracting data points...')
    datapoints = extract_datapoints_country_year(data)
    for c, df in datapoints.items():
        path = os.path.join(out_dir, 'ddf--datapoints--' + c + '--by--country--year.csv')
        df[c] = df[c].map(format_float_sigfig)
        df.to_csv(path, index=False)

    print('generating datapackage.json ...')
    dps = get_datapackage(out_dir, update=True)
    dump_json(os.path.join(out_dir, 'datapackage.json'), dps)
