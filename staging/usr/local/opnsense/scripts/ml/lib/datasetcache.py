"""
    Copyright (c) 2015-2020 Ad Schellevis <ad@opnsense.org>
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

    --------------------------------------------------------------------------------------

    shared module for suricata scripts, handles the installed datasets cache for easy access
"""

import fcntl
import glob
import os
import os.path
import shlex
import sqlite3
from configparser import ConfigParser
from datetime import datetime
from hashlib import md5

import ray
from django.db.models import Max
from ray.rllib.utils.framework import try_import_tf

from lib import dataset_source_directory
from ml.models.dataset import Dataset
from ml.models.dataset_properties import DatasetProperties
from ml.models.local_dataset_changes import LocalDatasetChanges
from ml.models.stats import Stats

tf1, tf, tfv = try_import_tf()
tf1.enable_eager_execution()

import common


class DatasetCache(object):
    """
    """

    def __init__(self):
        # suricata rule settings, source directory and cache json file to use
        self.cachefile = '%sdatasets.sqlite' % dataset_source_directory
        self._dataset_fields = ['sid', 'msg', 'rev', 'gid', 'source', 'enabled', 'reference', 'action']
        self._run, self._client = common.init_experiment('dataset-cache')

    @staticmethod
    def list_local():
        all_rule_files = []
        for filename in glob.glob('%s*/**/*.csv' % dataset_source_directory):
            all_rule_files.append(filename)

        return all_rule_files

    @staticmethod
    def list_local_changes():
        # parse OPNsense rule config
        rule_config_fn = ('%s../datasets.config' % dataset_source_directory)
        rule_config_mtime = os.stat(rule_config_fn).st_mtime
        rule_updates = {}
        if os.path.exists(rule_config_fn):
            cnf = ConfigParser()
            cnf.read(rule_config_fn)
            for section in cnf.sections():
                if section[0:5] == 'rule_':
                    sid = section[5:]
                    rule_updates[sid] = {'mtime': rule_config_mtime}
                    for rule_item in cnf.items(section):
                        rule_updates[sid][rule_item[0]] = rule_item[1]
        return rule_updates

    def list_datasets(self, filename):
        """ generator function to list rule file content including metadata
        :param filename:
        :return:
        """
        with open(filename, 'r') as f_in:
            source_filename = filename.split('/')[-1]
            dt = ray.data.read_csv(filename)
            dataset_info_record = {'dataset': filename, 'metadata': None}
            # md5_sum = md5(open(filename, 'rb').read()).hexdigest()
            filename_md5_sum = md5(filename.encode('utf-8')).hexdigest()
            count = dt.count()
            label_column = 'Label'
            features_types = [i for i in dt.schema() if i.name != label_column]
            features = [i.name for i in features_types]
            if count > 0:
                # define basic record
                record = {
                    'enabled': False,
                    'source': source_filename,
                    'sid': filename_md5_sum,
                    'rev': None,
                    'gid': None,
                    'msg': None,
                    'reference': None,
                    'classtype': '##none##',  # AI agents will recognize this attribute
                    'action': '',  # AI agents will recognize this attribute
                    'metadata': dict()
                }
                record['metadata']['artifact'] = filename
                record['metadata']['created_at'] = datetime.fromtimestamp(os.stat(filename).st_ctime).strftime(
                    '%Y_%m_%d')
                record['metadata']['updated_at'] = datetime.fromtimestamp(os.stat(filename).st_mtime).strftime(
                    '%Y_%m_%d')
                record['metadata']['count'] = count
                record['metadata']['features'] = ','.join(features)
                # record['metadata']['top_data'] = top_data

                if (label_column):
                    record['metadata']['label_column'] = label_column
                    features_float64 = [f.name for f in features_types if str(f.type) == 'double']
                    if any(i for i in dt.schema() if i.name == label_column and str(i.type) == 'string') and len(
                            features_float64) > 0:
                        output_signature = (
                            tf.TensorSpec(shape=(None, 1), dtype=tf.float64),
                            tf.TensorSpec(shape=(None), dtype=tf.string))
                        tfd = dt.to_tf(batch_size=1000000, label_column=label_column,
                                       feature_columns=[features_float64[0]], output_signature=output_signature)
                        labels = tfd.map(lambda _, x: tf.unique(x)[0]).reduce([''], lambda x, y:
                        tf.unique(tf.concat([x, y], 0))[0]).numpy().tolist()
                        del labels[0]

                        record['metadata']['labels'] = b','.join(labels).decode('utf-8')
                        record['metadata']['tag'] = b'_'.join(labels).replace(b' ', b'_').decode('utf-8')

                for f in features:
                    f_name = f.replace(' ', '_').lower()
                    record['metadata'][f_name] = True
                    # record['metadata']["%s:min" % f_name] = dt.min(f)
                    # record['metadata']["%s:max" % f_name] = dt.max(f)

                # record['metadata']['affected_product'] = None
                # record['metadata']['attack_target'] = None
                # record['metadata']['former_category'] = None
                # record['metadata']['deployment'] = None
                record['metadata']['signature_severity'] = 'Major'
                # record['metadata']['bugtraq'] = None
                # record['metadata']['cve'] = None

                # record['distance'] = 0
                record['reference'] = 'url,selks.ddns.net/archive/%s/threaded/' % record['metadata']['updated_at']

                dataset_info_record['metadata'] = record

            yield dataset_info_record

    def is_changed(self):
        """ check if datasets on disk are probably different from datasets in cache
        :return: boolean
        """
        if os.path.exists(self.cachefile):
            last_mtime = 0
            all_rule_files = self.list_local()
            for filename in all_rule_files:
                file_mtime = os.stat(filename).st_mtime
                if file_mtime > last_mtime:
                    last_mtime = file_mtime

            try:
                enough_table = Dataset.objects.exists() and DatasetProperties.objects.exists() \
                               and LocalDatasetChanges.objects.exists() and Stats.objects.exists()
                stats = Stats.objects.aggregate(Max('timestamp'), Max('files'))

                if enough_table and \
                        last_mtime == stats['timestamp__max'] and len(all_rule_files) == stats['files__max']:
                    return False
            except Exception:
                # if some reason the cache is unreadble, continue and report changed
                pass
        return True

    def create(self):
        """ create new cache
        :return: None
        """
        # lock create process
        lock = open(self.cachefile + '.LCK', 'w')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            # other process is already creating the cache, wait, let the other process do it's work and return.
            fcntl.flock(lock, fcntl.LOCK_EX)
            fcntl.flock(lock, fcntl.LOCK_UN)
            return

        # remove existing DB
        if os.path.exists(self.cachefile):
            os.remove(self.cachefile)

        db = sqlite3.connect(self.cachefile)
        db.text_factory = lambda x: str(x, 'utf-8', 'ignore')
        cur = db.cursor()

        cur.execute("create table stats (timestamp number, files number)")
        cur.execute("""create table datasets (sid TEXT, msg TEXT,
                                           rev INTEGER, gid INTEGER, reference TEXT,
                                           enabled BOOLEAN, action text, source TEXT)""")
        cur.execute("create table dataset_properties(sid TEXT, property text, value text) ")
        cur.execute("create table local_dataset_changes(sid text primary key, action text, last_mtime number)")
        last_mtime = 0
        all_rule_files = self.list_local()
        datasets_sql = 'insert into datasets(%(fieldnames)s) values (%(fieldvalues)s)' % {
            'fieldnames': (','.join(self._dataset_fields)),
            'fieldvalues': ':' + (',:'.join(self._dataset_fields))
        }
        dataset_prop_sql = 'insert into dataset_properties(sid, property, value) values (:sid, :property, :value)'
        for filename in all_rule_files:
            try:
                file_mtime = os.stat(filename).st_mtime
                if file_mtime > last_mtime:
                    last_mtime = file_mtime
                datasets = list()
                dataset_properties = list()
                for dataset_info_record in self.list_datasets(filename=filename):
                    if dataset_info_record['metadata'] is not None:
                        datasets.append(dataset_info_record['metadata'])
                        for prop in ['classtype']:
                            dataset_properties.append({
                                "sid": dataset_info_record['metadata']['sid'],
                                "property": prop,
                                "value": dataset_info_record['metadata'][prop]
                            })
                        for prop in dataset_info_record['metadata']['metadata']:
                            dataset_properties.append({
                                "sid": dataset_info_record['metadata']['sid'],
                                "property": prop,
                                "value": dataset_info_record['metadata']['metadata'][prop]
                            })

                cur.executemany(datasets_sql, datasets)
                cur.executemany(dataset_prop_sql, dataset_properties)
            except Exception as ex:
                print('loading fail filename=%s, %s' % (filename, ex))
                pass

        cur.execute('INSERT INTO stats (timestamp,files) VALUES (?,?) ', (last_mtime, len(all_rule_files)))
        cur.execute("""
                create table metadata_histogram as
                select distinct property, value, count(*) number_of_datasets
                from  dataset_properties
                where property not in ('created_at', 'updated_at')
                group by property, value
        """)
        db.commit()
        # release lock
        fcntl.flock(lock, fcntl.LOCK_UN)
        # import local changes (if changed)
        self.update_local_changes()

    def update_local_changes(self):
        """ read local datasets.config containing changes on installed dataset and update to "local_dataset_changes" table
        """
        if os.path.exists(self.cachefile):
            db = sqlite3.connect(self.cachefile)
            cur = db.cursor()
            cur.execute('select max(last_mtime) from local_dataset_changes')
            last_mtime = cur.fetchall()[0][0]
            rule_config_mtime = os.stat(('%s../datasets.config' % dataset_source_directory)).st_mtime
            if rule_config_mtime != last_mtime:
                # make sure only one process is updating this table
                lock = open(self.cachefile + '.LCK', 'w')
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except IOError:
                    # other process is already creating the cache, wait, let the other process do it's work and return.
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    fcntl.flock(lock, fcntl.LOCK_UN)
                    return
                # delete and insert local changes
                cur.execute('delete from local_dataset_changes')
                local_changes = self.list_local_changes()
                for sid in local_changes:
                    sql_params = (sid, local_changes[sid]['action'], local_changes[sid]['mtime'])
                    cur.execute('insert into local_dataset_changes(sid, action, last_mtime) values (?,?,?)', sql_params)
                db.commit()
                # release lock
                fcntl.flock(lock, fcntl.LOCK_UN)

    def search(self, limit, offset, filter_txt, sort_by):
        """ search installed datasets
        :param limit: limit number of rows
        :param offset: limit offset
        :param filter_txt: text to search, used format fieldname1,fieldname2/searchphrase include % to match on a part
        :param sort_by: order by, list of fields and possible asc/desc parameter
        :return: dict
        """
        result = {'rows': []}
        if os.path.exists(self.cachefile):
            db = sqlite3.connect(self.cachefile)
            cur = db.cursor()

            # construct query including filters
            sql_parameters = {}
            sql_filters = []
            prop_values = []
            rule_search_fields = ['msg', 'sid', 'source', 'installed_action']
            for filtertag in shlex.split(filter_txt):
                fieldnames, searchcontent = filtertag.split('/', maxsplit=1)
                sql_item = []
                for fieldname in [x.lower().strip() for x in fieldnames.split(',')]:
                    if fieldname in rule_search_fields:
                        # construct query string for rule table fields
                        if fieldname != fieldnames.split(',')[0].strip():
                            sql_item.append(' or ')
                        if searchcontent.find('*') == -1:
                            sql_item.append('cast(' + fieldname + " as text) like :" + fieldname + " ")
                        else:
                            sql_item.append('cast(' + fieldname + " as text) like '%'|| :" + fieldname + " || '%' ")
                        sql_parameters[fieldname] = searchcontent.replace('*', '')
                    else:
                        # property value combinations per rule are queried from the dataset_properties table
                        pfieldnm = "property_%d" % len(prop_values)
                        vfieldnm = "value_%d" % len(prop_values)
                        if searchcontent.find('*') == -1:
                            prop_values.append("property = :%s and value like :%s " % (pfieldnm, vfieldnm))
                        else:
                            prop_values.append(
                                "property = :%s and value like  '%'|| :%s  || '%'" % (pfieldnm, vfieldnm))
                        sql_parameters[pfieldnm] = fieldname
                        sql_parameters[vfieldnm] = searchcontent.replace('*', '')

                if len(sql_item) > 0:
                    sql_filters.append("".join(sql_item))

            sql = """select *
                     from (
                         select datasets.*, case when rc.action is null then datasets.action else rc.action end installed_action
                         from datasets
                  """

            if len(prop_values) > 0:
                sql_1 = "select sid, count(*) from dataset_properties where " + " or ".join(prop_values)
                sql_1 += " group by sid"
                sql_1 += " having count(*) = %d " % len(prop_values)
                sql += "inner join (%s) p on p.sid = datasets.sid " % sql_1
            sql += "left join local_dataset_changes rc on datasets.sid = rc.sid ) a"

            if len(sql_filters) > 0:
                sql += ' where ' + " and ".join(list(map(lambda x: " (%s)" % x, sql_filters)))

            # apply sort order (if any)
            sql_sort = []
            for sortField in sort_by.split(','):
                if sortField.split(' ')[0] in rule_search_fields:
                    if sortField.split(' ')[-1].lower() == 'desc':
                        sql_sort.append('%s desc' % sortField.split()[0])
                    else:
                        sql_sort.append('%s asc' % sortField.split()[0])

            # count total number of rows
            cur.execute('select count(*) from (%s) a' % sql, sql_parameters)
            result['total_rows'] = cur.fetchall()[0][0]

            if len(sql_sort) > 0:
                sql += ' order by %s' % (','.join(sql_sort))

            if str(limit) != '0' and str(limit).isdigit():
                sql += ' limit %s' % limit
                if str(offset) != '0' and str(offset).isdigit():
                    sql += ' offset %s' % offset

            # fetch results
            cur.execute(sql, sql_parameters)
            all_sids = []
            for row in cur.fetchall():
                record = {}
                for fieldNum in range(len(cur.description)):
                    record[cur.description[fieldNum][0]] = row[fieldNum]
                result['rows'].append(record)
                if record['sid']:
                    all_sids.append("%s" % record['sid'])

            # extend with collected metadata attributes
            cur.execute("select * from dataset_properties where sid in ('%s') order by sid" %
                        "','".join(all_sids)
                        )
            dataset_props = dict()
            for row in cur.fetchall():
                if row[0] not in dataset_props:
                    dataset_props[row[0]] = dict()
                dataset_props[row[0]][row[1]] = row[2]

            for record in result['rows']:
                if record['sid'] in dataset_props:
                    for fieldname in dataset_props[record['sid']]:
                        record[fieldname] = dataset_props[record['sid']][fieldname]
        return result

    def list_metadata(self):
        """
        :return: dictionary with known metadata types and values
        """
        result = {}
        if os.path.exists(self.cachefile):
            db = sqlite3.connect(self.cachefile)
            cur = db.cursor()
            cur.execute('SELECT property, value FROM metadata_histogram order by property, value')
            for record in cur.fetchall():
                if record[0] not in result:
                    result[record[0]] = list()
                result[record[0]].append(record[1])
        return result
