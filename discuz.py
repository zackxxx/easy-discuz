#!/usr/bin/env python2
# vim: set fileencoding=utf8

from __future__ import unicode_literals
import re
import asyncio
from bs4 import BeautifulSoup
import common
from httpcommon import HttpCommon
import repository


class Discuz(object):
    def __init__(self, concur_req=10, debug=False):
        self.debug = debug
        self.semaphore = asyncio.Semaphore(concur_req)
        self.todo = []
        self.pending_data = []
        self.cookies = {}
        self.reg = {
            'thread': re.compile(
                'normalthread_(?P<post_id>[\w\W]*?)">([\w\W]*?)<span id="thread_([\w\W]*?)"><a([\w\W]*?)">(?P<title>[\w\W]*?)</a>([\w\W]*?)uid=([\w\W]*?)">(?P<author_name>[\w\W]*?)</a>([\w\W]*?)<em>(?P<post_time>[\w\W]*?)</em>'),
            'photo': re.compile('file="attachments/([\w\W]*?)"')
        }
        self.base_url = common.get_config('DISCUZ', 'base_url')
        self.urls = {
            'base': self.base_url,
            'board': self.base_url + 'forumdisplay.php',
            'thread': self.base_url + 'viewthread.php',
            'attachment': self.base_url + 'attachments/%s',
        }

    def set_cookies(self, cookies):
        self.cookies = cookies
        return self

    def get_cookies(self):
        return self.cookies

    async def login(self):
        try:
            login_info = {'username': self.username, 'password': self.password,
                          'answer': '', 'handlekey': 'ls',
                          'questionid': '0', 'quickforward': 'yes',
                          'fastloginfield': 'username'}
            content = await HttpCommon.http_post(self.urls['login'], params=login_info, encoding=self.encoding)
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
            content = await HttpCommon.http_get(self.urls['board'],
                                                params=params,
                                                cookies=self.get_cookies())
            print('fetch thread {} succeed!'.format(fid))
            return parse(content)

    async def request_post(self, post_id):
        try:
            print('fetch post {} started!'.format(post_id))
            with (await self.semaphore):
                content = await HttpCommon.http_get(self.urls['thread'], params={'tid': post_id},
                                                    cookies=self.get_cookies())
                print('fetch post {} succeed!'.format(post_id))
                post_photos = re.findall(self.reg['photo'], content)
                sub_post_ids = re.findall(re.compile('id="postmessage_([\w\W]*?)"'), content)
                soup = BeautifulSoup(content, 'lxml')
                post_content = soup.find(id=('postmessage_' + sub_post_ids[0]))
                post_desc = post_content.get_text()

                thread = {
                    'digest': ('精华' in content) * 1,
                    'post_id': post_id,
                    'photos': post_photos,
                    'content': post_content,
                    'desc': post_desc,
                    'succeed': True,
                    'title': re.findall(re.compile('<h1>([\w\W]*?)</h1>'), content)[0]
                }

                return thread
        except Exception as e:
            print(e)
            return {
                'post_id': post_id,
                'succeed': False
            }

    def get_posts_list(self, fid, start_page, end_page, filter='digest', orderby='dateline'):
        print('分类 {}, {} 页 到 {} 页'.format(fid, start_page, end_page))
        posts_need_detail = common.run_futures(
            [self.request_thread(fid, page, filter, orderby) for page in range(start_page, end_page + 1)],
            repository.PostRepo.save_posts)

        return posts_need_detail

    def get_posts(self, posts):
        if posts is not None:
            details = common.run_futures([self.request_post(post['post_id']) for post in posts],
                                         repository.PostRepo.save_post_detail)
            return details

    def get_post(self, tid):
        detail = common.run_futures([self.request_post(tid)], repository.PostRepo.save_post_detail)
        return detail
