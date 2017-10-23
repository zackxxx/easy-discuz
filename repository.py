from peewee import *
from common import dd, get_config
from peewee import *
import datetime
import os
import json


def init_db():
    driver = get_config('DATABASE', 'driver')
    host = get_config(driver, 'host')
    username = get_config(driver, 'username')
    password = get_config(driver, 'password')
    database = get_config(driver, 'database')
    port = int(get_config(driver, 'port'))

    if driver == 'POSTGRESQL':
        db = PostgresqlDatabase(database, user=username, host=host, password=password)
    elif driver == 'SQLITE':
        from playhouse.sqlite_ext import SqliteExtDatabase
        db = SqliteExtDatabase(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/database.db'))
    elif driver == 'MYSQL':
        db = MySQLDatabase(database, user=username, host=host, password=password, port=port)
    else:
        raise NotSupportedError
    return db


db = init_db()


class BaseModel(Model):
    class Meta:
        database = db


class BaseModel(Model):
    class Meta:
        database = db

    @classmethod
    def get_or_none(cls, **kwargs):
        try:
            model = cls.get(**kwargs)
        except cls.DoesNotExist:
            return None
        else:
            return model

    @classmethod
    def primary_key(cls):
        return 'id'

    def __getitem__(self, item):
        return getattr(self, item)

    def dicts(self):
        r = {}
        for k in self._data.keys():
            r[k] = getattr(self, k)
        return r

    @classmethod
    def first_or_create(cls, check_attr, new_attr=None):
        try:
            if check_attr is None:
                return None

            model = cls.get(getattr(cls, cls.primary_key()) == check_attr.get(cls.primary_key()))
            # print('{} exist, skip'.format(video_info['view_id']))
        except cls.DoesNotExist:
            if new_attr is not None:
                check_attr.update(new_attr)
            model = cls.create(**check_attr)
            # print('save {}, success'.format(video_info['view_id']))

        return model


class Post(BaseModel):
    id = IntegerField(primary_key=True)
    post_id = CharField(null=True, unique=True)
    title = CharField(null=True, default=0)
    content = TextField(null=True)
    desc = TextField(null=True)
    photos = TextField(null=True)
    post_time = CharField(null=True)
    author_name = CharField(null=True)
    author_id = CharField(null=True)
    forum_id = CharField(null=True)
    downloaded = IntegerField(default=0)
    digest = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    @classmethod
    def primary_key(cls):
        return 'post_id'

    @classmethod
    def primary_key(cls):
        return 'post_id'


Post.create_table(True)
