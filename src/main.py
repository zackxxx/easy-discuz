from library import helper
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "library"))
from library import helper
from discuz import Discuz
import repository

if __name__ == '__main__':
    debug = bool(helper.get_config('APP', 'debug') == 1)
    base_url = repository.ConfigRepo.get_value('base_url')
    cookies = repository.ConfigRepo.get_value('cookies')
    concur = int(helper.get_config('APP', 'concur'))
    discuz = Discuz(base_url, concur, debug)
    post = discuz.post(261394)
    print(post)