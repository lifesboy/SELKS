"""
Django settings for scirius project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = "/var/lib/scirius/"
GIT_SOURCES_BASE_DIRECTORY = os.path.join(BASE_DIR, 'git-sources/')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# FIXME: generate this
SECRET_KEY = 'p7o6%vq))7h3li08c%k3id(wwo*u(^dbdmx2tv#t(tb2pr9@n-'
USE_ELASTICSEARCH = True
ELASTICSEARCH_ADDRESS = "localhost:9200"
ELASTICSEARCH_VERSION = 6
KIBANA_VERSION = 6
KIBANA_INDEX = ".kibana"
KIBANA_URL = "http://localhost:5601"
KIBANA6_DASHBOARDS_PATH = "/opt/selks/kibana6-dashboards/"
USE_KIBANA = True
KIBANA_PROXY = True

#SURICATA_UNIX_SOCKET = "/var/run/suricata/suricata-command.socket"

USE_EVEBOX = True
EVEBOX_ADDRESS = "localhost:5636"

USE_SURICATA_STATS = True
USE_LOGSTASH_STATS = True
STATIC_ROOT="/var/lib/scirius/static/"

DATABASES = {
  'default': {
     'ENGINE': 'django.db.backends.postgresql_psycopg2',
     'NAME': 'postgres',
     'USER':'postgres',
     'PASSWORD':'postgres',
     'HOST':'127.0.0.1',
     'PORT':'5432',
  }
}
DBBACKUP_STORAGE_OPTIONS = {'location': '/var/backups/'}

ELASTICSEARCH_LOGSTASH_ALERT_INDEX="logstash-alert-"

SURICATA_NAME_IS_HOSTNAME = True

ALLOWED_HOSTS=["*"]
ELASTICSEARCH_KEYWORD = "keyword"
USE_MOLOCH = True
MOLOCH_URL = "http://localhost:8005"
