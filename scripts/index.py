# -*- coding: utf-8 -*-
"""create ddf--index.csv"""

import csv
from pandas import DataFrame, concat
import os
import re

# global variables
out_dir = '/Users/semio/src/work/Gapminder/ddf--cdiac-co2/output'
index_columns = ['key', 'value', 'file']


def concept_index(path, concept_file):

    df = DataFrame([], columns=index_columns)

    with open(os.path.join(path, concept_file)) as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        header = reader.__next__()  # only get the headers. python3 only.

    header.remove('concept')
    df['value'] = header
    df['key'] = 'concept'
    df['file'] = concept_file

    return df


def entity_index(path, entity_file):

    df = DataFrame([], columns=index_columns)

    domain = re.match('ddf--entities--([\w_]+)-?.*', entity_file).groups()[0]
    with open(os.path.join(path, entity_file)) as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        header = reader.__next__()

    header.remove(domain)
    df['value'] = header
    df['key'] = domain
    df['file'] = entity_file

    return df


def datapoint_index(path, datapoint_file):
    df = DataFrame([], columns=index_columns)

    value, key = re.match('ddf--datapoints--([\w_]+)--by--(.*).csv', datapoint_file).groups()

    key = ','.join(key.split('--'))

    df['value'] = [value]
    df['key'] = [key]
    df['file'] = [datapoint_file]

    return df


def create_index_file(path, indexfile):
    fs = os.listdir(path)

    res = []
    for f in fs:
        if 'concept' in f:
            res.append(concept_index(path, f))
        if 'entities' in f:
            res.append(entity_index(path, f))
        if 'datapoints' in f:
            res.append(datapoint_index(path, f))

    res_df = concat(res)
    res_df = res_df.drop_duplicates()
    res_df.to_csv(indexfile, index=False)
