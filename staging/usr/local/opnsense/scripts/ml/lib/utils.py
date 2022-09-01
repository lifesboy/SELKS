import os
import subprocess
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
    file_df = file_df.sort_values(by='input_name').reset_index(drop=True)
    file_df = file_df.filter(['input_path', 'input_name', 'marked_done_path', 'st_mtime']).applymap(lambda i: [i])
    file_df['batch'] = file_df.apply(lambda i: i.name // batch_size, axis=1, result_type='reduce')

    batch_df: DataFrame = file_df.groupby('batch').sum()
    batch_df['output_name'] = batch_df.apply(lambda i: get_output_file_of_batch(i.input_name, tag, ext), axis=1, result_type='reduce')
    batch_df['output_path'] = batch_df.apply(lambda i: output, axis=1, result_type='reduce')
    return batch_df


def get_process_ids(script: str) -> map:
    script_command = "/bin/ps -ex | grep '%s' | grep -v 'grep' | grep -v '/bin/sh -c' | /usr/bin/awk '{print $1;}'" % script
    p_ids = subprocess.run(script_command, shell=True, capture_output=True, text=True).stdout.split('\n')
    return map(lambda i: int(i), set(p_ids) - set(['']))


def is_ray_gpu_ready() -> bool:
    script_command = "ray status | grep GPU"
    out = subprocess.run(script_command, shell=True, capture_output=True, text=True).stdout.strip()
    values = out.split(' ')[0].split('/')
    return len(values) > 1 and values[1].replace('.', '', 1).isdigit() and float(values[1]) > 0


def restart_ray_service() -> str:
    script_command = "service ray restart"
    out = subprocess.run(script_command, shell=True, capture_output=True, text=True).stdout.strip()
    return out


def lines_in_files_of(filter: str, file_pattern: str) -> DataFrame:
    # script_command = "fgrep -n '%s' %s" % ('Dst Port', '/cic/dataset/featured_extracted/cic2018/*')
    script_command = "fgrep -n '%s' %s" % (filter, file_pattern)
    lines = subprocess.run(script_command, shell=True, capture_output=True, text=True).stdout.split('\n')
    line_df = pd.DataFrame(map(lambda i: i.split(':'), lines[:-1]), columns=['file', 'line', 'text'])
    lines_df = line_df.groupby('file').agg(pd.Series.tolist).reset_index()
    lines_df['size'] = lines_df.apply(lambda i: len(i['line']), axis=1, result_type='reduce')
    lines_df = lines_df.loc[lines_df['size'] > 0]
    return lines_df


def separate_file_by_lines(fd) -> str:
    file = fd['file']
    size = fd['size']
    lines = fd['line']
    texts = list(map(lambda i: i.lower().replace(' ', '_').replace('/', '_'), fd['text']))
    cp_commands = [
        *["echo '%s' > %s.%s.csv" % (texts[i], file, i + 1) for i in range(0, size)],
        *["awk 'NR>%s && NR<%s' %s >> %s.%s.csv" % (lines[i], lines[i + 1], file, file, i + 1) for i in range(0, size - 1)],
        "awk 'NR>%s' %s >> %s.%s.csv" % (lines[-1], file, file, size),
        "mv %s %s.bak" % (file, file)
    ]
    return subprocess.run(' && '.join(cp_commands), shell=True, capture_output=True, text=True).stdout


def create_sampling(directory: str, files: []) -> str:
    commands = [
        "mkdir -p %s" % directory,
        *["ln -s '{}' '{}{:06d}.csv'".format(files[i], directory, i) for i in range(0, len(files))],
    ]
    return subprocess.run(' && '.join(commands), shell=True, capture_output=True, text=True).stdout


