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
from decimal import Decimal
from hashlib import md5
from itertools import starmap, chain, filterfalse

import ray
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import transaction
from django.db.models import Max, Value
from mlflow import ActiveRun
from mlflow.tracking import MlflowClient
from ray.rllib.utils.framework import try_import_tf

from ml.lib import dataset_source_directory
from ml.models import MetadataHistogram
from ml.models.dataset import Dataset
from ml.models.dataset_properties import DatasetProperties
from ml.models.local_dataset_changes import LocalDatasetChanges
from ml.models.stats import Stats

tf1, tf, tfv = try_import_tf()
tf1.enable_eager_execution()

from ml import common


class DatasetCache(object):
    """
    """
    _run: ActiveRun = None
    _client: MlflowClient = None

    def __init__(self):
        # suricata rule settings, source directory and cache json file to use
        self.cachefile = '%sdatasets.sqlite' % dataset_source_directory
        self._dataset_fields = ['sid', 'msg', 'rev', 'gid', 'source', 'enabled', 'reference', 'action']

    def init_experiment(self):
        if not self._run or not self._client:
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
        rule_updates = {}
        if os.path.exists(rule_config_fn):
            rule_config_mtime = os.stat(rule_config_fn).st_mtime
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
            self.init_experiment()
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
                # guarantee table is created in db
                Dataset.objects.exists()
                DatasetProperties.objects.exists()
                LocalDatasetChanges.objects.exists()
                Stats.objects.exists()

                stats = Stats.objects.aggregate(Max('timestamp'), Max('files'))

                return (Decimal(last_mtime).quantize(0) != stats['timestamp__max'].quantize(0)
                        or len(all_rule_files) != stats['files__max'])
            except Exception:
                # if some reason the cache is unreadble, continue and report changed
                pass
        return True

    # @transaction.atomic
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

        # remove existing data
        Dataset.objects.all().delete()
        DatasetProperties.objects.all().delete()
        Stats.objects.all().delete()
        LocalDatasetChanges.objects.all().delete()
        if os.path.exists(self.cachefile):
            os.remove(self.cachefile)

        last_mtime = 0
        all_rule_files = self.list_local()
        for filename in all_rule_files:
            try:
                file_mtime = os.stat(filename).st_mtime
                if file_mtime > last_mtime:
                    last_mtime = file_mtime
                datasets = list()
                dataset_properties = list()
                for dataset_info_record in self.list_datasets(filename=filename):
                    if dataset_info_record['metadata'] is not None:
                        metadata = dataset_info_record['metadata']
                        datasets.append(Dataset(sid=metadata['sid'],
                                                msg=metadata['msg'],
                                                rev=metadata['rev'],
                                                gid=metadata['gid'],
                                                reference=metadata['reference'],
                                                enabled=metadata['enabled'],
                                                action=metadata['action'],
                                                source=metadata['source'],
                                                updated_at=metadata['metadata']['updated_at'],
                                                created_at=metadata['metadata']['created_at']))
                        for prop in ['classtype']:
                            dataset_properties.append(DatasetProperties(
                                sid=dataset_info_record['metadata']['sid'],
                                property=prop,
                                value=dataset_info_record['metadata'][prop]
                            ))
                        for prop in dataset_info_record['metadata']['metadata']:
                            dataset_properties.append(DatasetProperties(
                                sid=dataset_info_record['metadata']['sid'],
                                property=prop,
                                value=dataset_info_record['metadata']['metadata'][prop]
                            ))

                Dataset.objects.bulk_create(datasets)
                DatasetProperties.objects.bulk_create(dataset_properties)
            except Exception as ex:
                print('loading fail filename=%s, %s' % (filename, ex))
                pass

        Stats(timestamp=last_mtime, files=len(all_rule_files)).save()
        os.system('touch {}'.format(self.cachefile))
        # release lock
        fcntl.flock(lock, fcntl.LOCK_UN)
        # import local changes (if changed)
        self.update_local_changes()

    # @transaction.atomic
    def update_local_changes(self):
        """ read local datasets.config containing changes on installed dataset and update to "local_dataset_changes" table
        """
        if os.path.exists(self.cachefile):
            last_mtime = LocalDatasetChanges.objects.aggregate(Max('last_mtime'))['last_mtime__max']

            # todo
            # rule_config_mtime = os.stat(('%s../datasets.config' % dataset_source_directory)).st_mtime
            if not last_mtime or last_mtime > 0:  # rule_config_mtime != last_mtime:
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
                LocalDatasetChanges.objects.all().delete()
                local_changes = self.list_local_changes()
                for sid in local_changes:
                    LocalDatasetChanges(sid=sid, action=local_changes[sid]['action'],
                                        last_mtime=local_changes[sid]['mtime']).save()
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
            # construct query including filters
            sql_parameters = {}
            sql_filters = []
            prop_values = []
            rule_search_fields = ['msg', 'sid', 'source', 'installed_action']

            fields_content = map(lambda i: i.split('/', maxsplit=1), shlex.split(filter_txt))
            fc_list = starmap(lambda f, _: list(map(lambda i, c=_: (f.lower().strip(), c), f.split(','))), fields_content)
            fc = list(chain(*fc_list))

            fc_dataset = filterfalse(lambda f, _, a=rule_search_fields: f in a, fc)
            fc_properties = filter(lambda f, _, a=rule_search_fields: f not in a, fc)

            fcd_queries = starmap(lambda f, c: 'cast({} as text) like %{}%'.format(f, c), fc_dataset)
            fcp_queries = starmap(lambda f, c: 'property={} and value like %{}%'.format(f, c), fc_properties)

            for filtertag in shlex.split(filter_txt):
                fieldnames, searchcontent = filtertag.split('/', maxsplit=1)
                sql_item = []
                for fieldname in [x.lower().strip() for x in fieldnames.split(',')]:
                    if fieldname in rule_search_fields:
                        # construct query string for rule table fields
                        if fieldname != fieldnames.split(',')[0].strip():
                            sql_item.append(' or ')
                        if searchcontent.find('*') == -1:
                            sql_item.append('cast(' + fieldname + " as text) like %(" + fieldname + ")s ")
                        else:
                            sql_item.append('cast(' + fieldname + " as text) like '%%(" + fieldname + ")s%' ")
                        sql_parameters[fieldname] = searchcontent.replace('*', '')
                    else:
                        # property value combinations per rule are queried from the dataset_properties table
                        pfieldnm = "property_%d" % len(prop_values)
                        vfieldnm = "value_%d" % len(prop_values)
                        if searchcontent.find('*') == -1:
                            prop_values.append("property = %({})s and value like %({})s ".format(pfieldnm, vfieldnm))
                        else:
                            prop_values.append("property = %({})s and value like '%%({})s%'".format(pfieldnm, vfieldnm))
                        sql_parameters[pfieldnm] = fieldname
                        sql_parameters[vfieldnm] = searchcontent.replace('*', '')

                if len(sql_item) > 0:
                    sql_filters.append("".join(sql_item))

            sql = """select *
                     from (
                         select ml_dataset.*, case when rc.action is null then ml_dataset.action else rc.action end installed_action
                         from ml_dataset
                  """

            if len(prop_values) > 0:
                sql_1 = "select sid, count(*) from ml_datasetproperties where " + " or ".join(prop_values)
                sql_1 += " group by sid"
                sql_1 += " having count(*) = %d " % len(prop_values)
                sql += "inner join (%s) p on p.sid = ml_dataset.sid " % sql_1
            sql += "left join ml_localdatasetchanges rc on ml_dataset.sid = rc.sid ) a"

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

            fc_sort = map(lambda x: map(lambda i: (i[0], i[-1].lower()), x.split(' ')), sort_by.split(','))
            fcs_query = map(lambda f, c: '%s %s' % (f, c if c == 'desc' else 'asc'), fc_sort)

            # count total number of rows
            #cur.execute('select count(*) from (%s) a' % sql, sql_parameters)
            result['total_rows'] = list(DatasetProperties.objects.raw('select 1 id, count(*) from (%s) a' % sql, sql_parameters))[0].count

            if len(sql_sort) > 0:
                sql += ' order by %s' % (','.join(sql_sort))

            if str(limit) != '0' and str(limit).isdigit():
                sql += ' limit %s' % limit
                if str(offset) != '0' and str(offset).isdigit():
                    sql += ' offset %s' % offset

            # fetch results
            #cur.execute(sql, sql_parameters)
            datasets = list(Dataset.objects.raw(sql, sql_parameters))

            all_sids = filter(None, map(lambda i: i.sid, datasets))
            dataset_props = DatasetProperties.objects.filter(sid__in=all_sids)
            dpm = dict(map(lambda i: (i.sid, i), dataset_props))

            result['rows'] = list(map(lambda i: {
                **i.__dict__,
                **dpm[i.sid].__dict__,
                **{'_state': None, 'id': None}
            } if dpm[i.sid] else i, datasets))

            #for row in cur.fetchall():
            #for row in datasets:
            #    record = {}
            #    #for fieldNum in range(len(cur.description)):
            #    #    record[cur.description[fieldNum][0]] = row[fieldNum]
            #    #result['rows'].append(record)
            #    #if record['sid']:
            #    #    all_sids.append("%s" % record['sid'])
            #
            # extend with collected metadata attributes
            # cur.execute("select * from dataset_properties where sid in ('%s') order by sid" %
            #            "','".join(all_sids)
            #            )



            #dataset_props = dict()
            #for row in cur.fetchall():
            #    if row[0] not in dataset_props:
            #        dataset_props[row[0]] = dict()
            #    dataset_props[row[0]][row[1]] = row[2]
            #
            #for record in result['rows']:
            #    if record['sid'] in dataset_props:
            #        for fieldname in dataset_props[record['sid']]:
            #            record[fieldname] = dataset_props[record['sid']][fieldname]
        return result

    def list_metadata(self):
        """
        :return: dictionary with known metadata types and values
        """
        result = {}
        if os.path.exists(self.cachefile):
            histogram = (MetadataHistogram.objects
                         .values('property', 'value')
                         .annotate(values=ArrayAgg('value', default=Value([])))
                         .values_list('property', 'values')
                         .order_by('property'))
            result = dict([(prop, sorted(values)) for prop, values in histogram])

        return result
