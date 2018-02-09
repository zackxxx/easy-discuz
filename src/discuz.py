#!/usr/bin/env python2
# vim: set fileencoding=utf8

import re
import asyncio
from bs4 import BeautifulSoup

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "library"))
from library import helper
from library.http import HttpCommon


class Discuz(object):
    def __init__(self, base_url, concur_req=10, debug=False):
        if not base_url:
            raise Exception('base url is none')

        self.debug = debug
        self.semaphore = asyncio.Semaphore(concur_req)
        self.cookies = {}
        self.reg = {
            'thread': re.compile(
                'normalthread_(?P<post_id>[\w\W]*?)">([\w\W]*?)<span id="thread_([\w\W]*?)"><a([\w\W]*?)">(?P<title>[\w\W]*?)</a>([\w\W]*?)uid=([\w\W]*?)">(?P<author_name>[\w\W]*?)</a>([\w\W]*?)<em>(?P<post_time>[\w\W]*?)</em>'),
            'photo': re.compile('file="attachments/([\w\W]*?)"')
        }
        self.base_url = base_url
        self.urls = {
            'base': self.base_url,
            'thread': self.base_url + 'forumdisplay.php',
            'post': self.base_url + 'viewthread.php',
            'attachment': self.base_url + 'attachments/%s',
        }

    def set_cookies(self, cookies):
        self.cookies = cookies
        return self

    def get_cookies(self):
        return self.cookies

    async def login(self, username, password):
        try:
            login_info = {'username': username, 'password': password,
                          'answer': '', 'handlekey': 'ls',
                          'questionid': '0', 'quickforward': 'yes',
                          'fastloginfield': 'username'}
            content = await HttpCommon.post(self.urls['login'], params=login_info, encoding=self.encoding)
            if self.debug:
                print(content)

            if self.username in content:
                self.set_cookies(HttpCommon.cookies)
                return True

            return False
        except Exception as e:
            if self.debug:
                print(e)
            return None

    def threads(self, fid, start_page, end_page=0, filter='digest', orderby='dateline', handler=None,
                handler_args=None):
        helper.logger(__name__).info('分类 {}, {} 页 到 {} 页'.format(fid, start_page, end_page))
        is_single_thread = end_page == 0
        if is_single_thread:
            end_page = start_page
        digest_posts = helper.run_futures(
            [self.request_thread(fid, page, filter, orderby) for page in range(start_page, end_page + 1)],
            handler=handler,
            handler_args=handler_args)

        if is_single_thread:
            return digest_posts[0]

        return digest_posts

    def posts(self, post_ids, handler=None, handler_args=None):
        if not isinstance(post_ids, list):
            post_ids = [post_ids]

        detail = helper.run_futures([self.request_post(tid) for tid in post_ids],
                                    handler=handler,
                                    handler_args=handler_args)
        return detail

    def post(self, post_id, handler=None, handler_args=None):

        detail = helper.run_futures([self.request_post(post_id)],
                                    handler=handler,
                                    handler_args=handler_args)
        return detail[0]

    async def request_thread(self, fid, page=1, filter='digest', orderby='dateline'):
        def parse(content):
            raw_threads = re.findall(self.reg['thread'], content)
            threads = []
            for raw_thread in raw_threads:
                thread = {
                    'forum_id': int(fid),
                    'digest': ('精华' in raw_thread[5]) * 1,
                    'post_id': int(raw_thread[0]),
                    'title': raw_thread[4],
                    'author_id': raw_thread[6],
                    'author_name': raw_thread[7],
                    'post_time': raw_thread[9]
                }
                threads.append(thread)

            print('fetch thread count {}'.format(len(threads)))
            return threads

        print('fetch thread {} started!'.format(fid))

        with (await self.semaphore):
            params = {'fid': fid, 'page': page, 'orderby': orderby}
            if filter:
                params['filter'] = filter
            content = await HttpCommon.get(self.urls['thread'],
                                           params=params,
                                           cookies=self.get_cookies())
            print('fetch thread {} succeed!'.format(fid))
            return parse(content)

    async def request_post(self, post_id, with_meta=False):
        try:
            print('fetch post {} started!'.format(post_id))
            with (await self.semaphore):
                content = await HttpCommon.get(self.urls['post'], params={'tid': post_id},
                                               cookies=self.get_cookies())
                print('fetch post {} succeed!'.format(post_id))
                post_photos = re.findall(self.reg['photo'], content)
                sub_post_ids = re.findall(re.compile('id="postmessage_([\w\W]*?)"'), content)
                soup = BeautifulSoup(content, 'lxml')
                post_content = soup.find(id=('postmessage_' + sub_post_ids[0]))
                post_desc = post_content.get_text()

                if with_meta:
                    author_id, author_name = \
                        re.findall(re.compile('href="space\.php\?uid=([\d]*?)" target="_blank">([\w\W]*?)</a>'),
                                   content)[0]
                    post_date, post_time = re.findall(re.compile('span title="([\w\W]*?) ([\w\W]*?)"'), content)[0]

                post = {
                    'digest': ('精华' in content) * 1,
                    'post_id': post_id,
                    'photos': post_photos,
                    'content': post_content,
                    'desc': post_desc,
                    'succeed': True,
                    'title': re.findall(re.compile('<h1>([\w\W]*?)</h1>'), content)[0]
                }

                if with_meta:
                    post.update({
                        'author_id': author_id,
                        'author_name': author_name,
                        'post_time': post_date,
                    })

                return post
        except Exception as e:
            print(e)
            return {
                'post_id': post_id,
                'succeed': False
            }

    def post_url(self, post_id):
        return self.urls['post'] + '?tid={}'.format(post_id)

    def thread_url(self, fid, params={}):
        from urllib.parse import urlencode
        params['tid'] = fid
        return self.urls['post'] + '?tid={}{}'.format(urlencode(params))

    def render_post(self, post):
        image_count = 0
        image_total = len(post['photos'])
        post['desc'] = '\n'.join(list(filter(lambda line: len(line) > 3, post['desc'].splitlines())))
        desc = ''
        replace = []
        split_count = 100
        split_name = '\n=========================\n'
        for num, line in enumerate(post['desc'].splitlines()):
            line = line.replace('{', '').replace('}', '')

            if num in replace:
                continue
            if '下载 (' in line:
                image_count += 1
                desc += '\n{}'
                replace = [num + 1]

                if image_count % split_count == 0 and (image_total - image_count) > split_count // 2:
                    desc += split_name

            else:
                desc = desc + '\n' + line

        if image_total - image_count > 0:
            for i in range(1, image_total - image_count + 1):
                desc += '\n{}'
                if i % split_count == 0 and (image_total - i) > split_count // 2:
                    desc += split_name

        post['desc'] = desc.format(
            *('<img src="{}">'.format(self.base_url + 'attachments/%s' % photo_id) for
              photo_id in
              post['photos']))
        post['contents'] = post['desc'].split(split_name)
        return post
