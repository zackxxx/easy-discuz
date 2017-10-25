import os
import configparser
import asyncio
import tqdm


def dd(content):
    print(type(content))
    print(content)
    exit(1)


def get_config(*config_key):
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_path)
    return config.get(*config_key)


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


class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
