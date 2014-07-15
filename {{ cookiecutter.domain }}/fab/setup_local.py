from __future__ import print_function, unicode_literals

import os
import platform

from fabric.api import settings, task
from fabric.colors import green, red
from fabric.contrib.console import confirm

from fab.config import CONFIG, local, get_random_string


@task(default=True)
def setup():
    if os.path.exists('venv'):
        print(red('It seems that this project is already set up, aborting.'))
        return 1

    local('virtualenv --python python2.7 --prompt "(venv:{domain})" venv')
    if platform.system() == 'Darwin' and platform.mac_ver()[0] >= '10.9':
        local(
            'export CFLAGS=-Qunused-arguments'
            ' && export CPPFLAGS=-Qunused-arguments'
            ' && venv/bin/pip install -r requirements/dev.txt')
    else:
        local('venv/bin/pip install -r requirements/dev.txt')

    with open('%(project_name)s/local_settings.py' % CONFIG, 'w') as f:
        CONFIG['secret_key'] = get_random_string(50)
        f.write('''\
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '%(database_name)s',
    }
}
SECRET_KEY = '%(secret_key)s'
RAVEN_CONFIG = {
    'dsn': '',  # Unused in local development.
}
ALLOWED_HOSTS = ['*']
''' % CONFIG)

    local('cd {sass} && npm install')
    local('cd {sass} && bower install')

    local('createdb {database_name} --encoding=UTF8 --template=template0')
    local('venv/bin/python manage.py syncdb --noinput')
    local('venv/bin/python manage.py migrate --noinput medialibrary')
    local('venv/bin/python manage.py migrate --noinput elephantblog')
    local('venv/bin/python manage.py migrate --noinput form_designer')
    local('venv/bin/python manage.py migrate --noinput page')
    local('venv/bin/python manage.py migrate --noinput')

    print(green(
        'Initial setup has completed successfully!', bold=True))
    print(green(
        'Next steps:'))
    print(green(
        '- Create a superuser: venv/bin/python manage.py createsuperuser'))
    print(green(
        '- Run the development server: fab dev'))
    print(green(
        '- Create a Bitbucket repository: fab versioning.init_bitbucket'))
    print(green(
        '- Configure {server_name} for this project: fab setup_server'))


@task
def pull_database():
    if not confirm('Completely replace the local database (if it exists)?'):
        return

    with settings(warn_only=True):
        local('dropdb {database_name}')

    local('createdb {database_name} --encoding=UTF8 --template=template0')
    local(
        'ssh {server} "source .profile &&'
        ' pg_dump {database_name} --no-privileges --no-owner --no-reconnect"'
        ' | psql {database_name}')


@task
def pull_mediafiles():
    if not confirm('Completely replace local mediafiles?'):
        return
    local('rsync -avz --delete {server}:{domain}/media .')
