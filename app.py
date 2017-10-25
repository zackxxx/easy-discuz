import os
import configparser
import asyncio
import tqdm
import peewee

import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'config')))
import config.log





class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


def dd(content):
    print(type(content))
    print(content)
    exit(1)


def get_config(*config_key):
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_path)
    if len(config_key) > 1:
        return config.get(*config_key)
    return config[config_key[0]]


def trans_lists_to_dict(l):
    data = {}
    for dic in l:
        data.update(dic)
    return data


async def futures(todo, handler=None, handler_args=None):
    results = []
    todo_iter = asyncio.as_completed(todo)
    todo_iter = tqdm.tqdm(todo_iter, total=len(todo))
    for future in todo_iter:
        res = await future
        if handler is not None:
            if handler_args is not None:
                res = handler(res, *handler_args)
            else:
                res = handler(res)
            results.append(res)
    return results


def run_futures(todo, handler=None, handler_args=None):
    loop = asyncio.get_event_loop()
    data = loop.run_until_complete(futures(todo, handler=handler, handler_args=handler_args))
    return data


def logger(name):
    return config.log.logging.getLogger(name)


def init_db():
    driver = get_config('DATABASE', 'driver')
    config = get_config(driver)

    if driver == 'POSTGRESQL':
        db = peewee.PostgresqlDatabase(config['database'], user=config['username'], host=config['host'],
                                       password=config['password'], port=int(config['port']))
    elif driver == 'SQLITE':
        from playhouse.sqlite_ext import SqliteExtDatabase
        db = SqliteExtDatabase(os.path.join(os.path.dirname(os.path.abspath(__file__)), config['database']))
    elif driver == 'MYSQL':
        db = peewee.MySQLDatabase(config['database'], user=config['username'], host=config['host'],
                                  password=config['password'], port=int(config['port']))
    else:
        raise peewee.NotSupportedError
    return db
