from library import helper
import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "library"))
from library import helper
from discuz import Discuz
import repository
import argparse


class DiscuzCrawler(object):
    def __init__(self, corcur_req=10, debug=False, cookies=None):
        self.discuz = Discuz(concur_req=corcur_req, debug=debug).set_cookies(cookies)
        self.threads_need_login = []
        self.threads_no_need_login = [19, 21]

    def run(self, fids, with_detail=True):
        for fid_info in fids:
            if fid_info[0] in self.threads_no_need_login:
                self.discuz.set_cookies({})
            threads_posts = self.crawl_thread_posts(*fid_info)
            if with_detail:
                for posts in threads_posts:
                    self.crawl_detail_posts([post['post_id'] for post in posts])

    def update_detail(self, fid=None):
        step = 100
        offset = 0
        while True:
            posts = repository.PostRepo.get_need_detail(step, 0, fid)
            if posts.count() == 0:
                helper.logger(__name__).info('noting to update !')
                break
            self.crawl_detail_posts([post['post_id'] for post in posts])
            helper.logger(__name__).info([post['post_id'] for post in posts])
            offset += step
            helper.logger(__name__).info('offset {}'.format(offset))

    def crawl_thread_posts(self, fid, start_page, end_page, filter='digest', orderby='dateline'):
        thread_posts = self.discuz.threads(fid, start_page, end_page, filter, orderby, repository.PostRepo.save_posts)
        return thread_posts

    def crawl_detail_posts(self, post_ids):
        if isinstance(post_ids, int):
            post_ids = [post_ids]
        if post_ids is not None:
            details = self.discuz.posts(post_ids, repository.PostRepo.save_post_detail)
            return details
        return None


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--post', help='post id')
    parser.add_argument('-f', '--forum', help='forum id')
    parser.add_argument('--detail', type=bool, default=False, help='get forum posts digest')
    parser.add_argument('--start', default=1, type=int, help='start page')
    parser.add_argument('--end', default=5, type=int, help='end page')
    parser.add_argument('--filter', default='digest', help='filter page ')
    parser.add_argument('--update', help='update detail of exist digest posts')
    args = vars(parser.parse_args())

    debug = bool(helper.get_config('APP', 'debug') == 1)
    base_url = repository.ConfigRepo.get_value('base_url')
    cookies = repository.ConfigRepo.get_value('cookies')
    concur = int(helper.get_config('APP', 'concur'))
    crawler = DiscuzCrawler(concur, debug, cookies)

    if args.get('post', None):
        crawler.crawl_thread_posts(args['post'])
        exit()

    if args.get('update'):
        crawler.update_detail(args.get('forum'))
        exit()

    if args.get('forum'):
        filter_type = args.get('filter', 'digest')
        if filter_type == 'all':
            filter_type = None
        fids = [
            (args['forum'], args.get('start'), args.get('end'), filter_type),
        ]
    else:
        fids = [
            (19, 1, 5),
            (21, 1, 5),
        ]

    with_detail = args['detail']
    crawler.run(fids, with_detail)
