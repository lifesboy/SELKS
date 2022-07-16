import os
from datetime import datetime

import pandas as pd
from pandas import DataFrame

import hashlib


def marked_done(files: []) -> bool:
    t = str(datetime.now())
    fs = list(map(lambda i: open(i, 'w'), files))
    list(map(lambda i: i.write(t), fs))
    list(map(lambda i: i.close(), fs))
    return True


def get_output_file_of_batch(names: [], tag: str = '_', ext: str = '') -> str:
    return '%s.%s_%s%s' % ('_'.join(names), tag, datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), ext)


def get_marked_done_file_name(file: str, tag: str = '_') -> str:
    return '.%s.%s.done' % (hashlib.sha256(file.encode('utf-8')).hexdigest(), tag)


def get_processing_file_pattern(
        input_files: [], output: str, ext: str = '', tag: str = '_', batch_size: int = 10) -> DataFrame:
    file_df: DataFrame = pd.DataFrame(input_files, columns=['input_path'])
    file_df['st_mtime'] = file_df.apply(lambda i: os.stat(i.input_path).st_mtime, axis=1, result_type='reduce')
    file_df['st_size'] = file_df.apply(lambda i: os.stat(i.input_path).st_size, axis=1, result_type='reduce')
    file_df = file_df[file_df['st_size'] > 0]
    file_df['input_name'] = file_df.apply(lambda i: os.path.split(i.input_path)[-1], axis=1, result_type='reduce')
    file_df['marked_done_name'] = file_df.apply(lambda i: get_marked_done_file_name(i.input_path, tag), axis=1, result_type='reduce')
    file_df['marked_done_path'] = file_df.apply(lambda i: os.path.join(output, i.marked_done_name), axis=1, result_type='reduce')
    file_df['marked_done_existed'] = file_df.apply(lambda i: os.path.exists(i.marked_done_path), axis=1, result_type='reduce')

    file_df = file_df.loc[file_df['marked_done_existed'] == False]
    file_df = file_df.sort_values(by='input_name')
    file_df = file_df.filter(['input_path', 'input_name', 'marked_done_path', 'st_mtime']).applymap(lambda i: [i])
    file_df['batch'] = file_df.apply(lambda i: i.name // batch_size, axis=1, result_type='reduce')

    batch_df: DataFrame = file_df.groupby('batch').sum()
    batch_df['output_name'] = batch_df.apply(lambda i: get_output_file_of_batch(i.input_name, tag, ext), axis=1, result_type='reduce')
    batch_df['output_path'] = batch_df.apply(lambda i: os.path.join(output, i.output_name), axis=1, result_type='reduce')
    return batch_df