# -*- coding: utf-8 -*-

from ddf_utils.factory import IGMELoader


source_path = '../source/'
source_name = 'UNIGME-Rates-Deaths_Under5'

if __name__ == '__main__':
    print('updating source files...')
    IGMELoader().bulk_download(source_path, name=source_name)
