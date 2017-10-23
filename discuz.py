#!/usr/bin/env python2
# vim: set fileencoding=utf8

from __future__ import unicode_literals

import re
import asyncio
from bs4 import BeautifulSoup
import json

from mycoro import MyCoro

from common import dd, get_config
from httpcommon import HttpCommon
from repository import Post

thread_reg = re.compile(
    'normalthread_(?P<post_id>[\w\W]*?)">([\w\W]*?)<span id="thread_([\w\W]*?)"><a([\w\W]*?)">(?P<title>[\w\W]*?)</a>([\w\W]*?)uid=([\w\W]*?)">(?P<author_name>[\w\W]*?)</a>([\w\W]*?)<em>(?P<post_time>[\w\W]*?)</em>')
photo_reg = re.compile('file="attachments/([\w\W]*?)"')

BASE_URL = get_config('DISCUZ', 'base_url')
BOARD_URL = BASE_URL + 'forumdisplay.php'
THREAD_URL = BASE_URL + 'viewthread.php'
ATTACHMENT_URL = BASE_URL + 'attachments/%s'


class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class Discuz(object):
    def __init__(self, concur_req=10, verbose=False):
        self.coro = MyCoro()
        self.loop = asyncio.get_event_loop()
        self.post_exist = 0
        self.break_count_post_exist = 5
        self.verbose = verbose
        self.semaphore = asyncio.Semaphore(concur_req)
        self.todo = []
        self.pending_data = []
        self.cookies = {}

    def set_cookies(self, cookies):
        self.cookies = cookies
        return self

    def get_cookies(self):
        return self.cookies

    async def thread_posts(self, fid, page=1, filter='digest', orderby='dateline'):
        def parse(content):
            raw_threads = re.findall(thread_reg, content)
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
            return threads

        print('fetch thread {} started!'.format(fid))

        with (await self.semaphore):
            content = await HttpCommon.http_get(BOARD_URL,
                                                params={'fid': fid, 'filter': filter, 'page': page, 'orderby': orderby},
                                                cookies=self.get_cookies())
            print('fetch thread {} succeed!'.format(fid))
            return parse(content)

    async def post_detail(self, tid, all=True):
        try:
            print('fetch post {} started!'.format(tid))
            with (await self.semaphore):
                content = await HttpCommon.http_get(THREAD_URL, params={'tid': tid},
                                                    cookies=self.get_cookies())
                print('fetch post {} succeed!'.format(tid))
                post_photos = re.findall(photo_reg, content)
                sub_post_ids = re.findall(re.compile('id="postmessage_([\w\W]*?)"'), content)
                soup = BeautifulSoup(content, 'lxml')
                post_content = soup.find(id=('postmessage_' + sub_post_ids[0]))
                post_desc = post_content.get_text()

                thread = {
                    'digest': ('精华' in content) * 1,
                    'post_id': tid,
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
                'post_id': tid,
                'succeed': False
            }

    def get_lists(self, fid, start_page, end_page, filter='digest', orderby='dateline'):
        desc = '分类 {}, {} 页 到 {} 页'.format(fid, start_page, end_page)
        items_need_detail = self.coro.set_todo(
            [self.thread_posts(fid, page, filter, orderby) for page in range(start_page, end_page + 1)]).run(
            desc, self.save_posts)
        return items_need_detail

    def get_posts_detail(self, posts):
        desc = '详情'
        if posts is not None:
            details = self.coro.set_todo([self.post_detail(post['post_id']) for post in posts]).run(desc,
                                                                                                    self.save_post_detail)
            return details

    def get_detail(self, tid):
        detail = self.coro.set_todo([self.post_detail(tid)]).run('', self.save_post_detail)
        return detail

    @staticmethod
    def trans_lists_to_dict(l):
        data = {}
        for dic in l:
            data.update(dic)

        return data

    def save_posts(self, thread_items):
        if not thread_items or len(thread_items) <= 0:
            self.post_exist = self.break_count_post_exist + 1
            return None

        items_need_detail = []
        for key, item in enumerate(thread_items):
            post = Post.get_or_none(post_id=item['post_id'])
            if post is None:
                post = Post.create(
                    **{k: item[k] for k in
                       ['post_id', 'title', 'author_id', 'author_name', 'post_time', 'forum_id', 'digest']})
                print('save! digest post ', post.post_id)
                items_need_detail.append(item)
            else:
                print('skip! digest post ', item['post_id'])
                self.post_exist += 1
                if not post.photos:
                    items_need_detail.append(item)
        print('Exist digest count {}, Need detail posts count {}'.format(self.post_exist,
                                                                         len(items_need_detail)))
        return items_need_detail

    @staticmethod
    def save_post_detail(item):
        post_id = item['post_id']
        post = Post.get_or_none(post_id=post_id)

        if item['succeed']:
            if post:
                if not post.photos or (len(json.loads(post.photos)) < len(item['photos'])):
                    post.content = str(item['content'])
                    post.desc = item['desc']
                    post.photos = json.dumps(item['photos'])
                    post.save()
                    print('post {} detail updated ! '.format(post_id))
                else:
                    print('post {} detail exist, noting to update !'.format(post_id))
            else:
                item['author_id'] = post.author_id
                post = Post.create(**{k: item[k] for k in
                                      ['post_id', 'title', 'content', 'desc', 'author_id', 'author_name', 'post_time',
                                       'digest']})
                print('post {} detail created and updated! '.format(post_id))
        else:
            if post:
                print('post {} detail fetch fail!'.format(post_id))
                post.photos = json.dumps([])
                post.save()
        return post
