import app
import json
import os
import repository

from discuz import Discuz
import argparse


class DiscuzCrawler(object):
    def __init__(self, corcur_req=10, debug=False):
        self.discuz = self.init_discuz(corcur_req, debug)

    @staticmethod
    def init_discuz(corcur_req, debug):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json'), 'r') as f:
            cookies = json.loads(f.read())
        return Discuz(concur_req=corcur_req, debug=debug).set_cookies(cookies)

    def update_discuz(self, fids, with_detail=True):
        for fid_info in fids:
            if fid_info[0] in [19, 21]:
                self.discuz.set_cookies({})
            threads_posts = self.discuz.get_posts_list(*fid_info)
            if with_detail:
                for posts in threads_posts:
                    self.discuz.get_posts(posts)

    def update_detail_from_database(self):
        step = 100
        offset = 0
        while True:
            posts = repository.PostRepo.get_need_detail(step)
            if posts.count() == 0:
                break
            self.discuz.get_posts(posts)
            print([post['post_id'] for post in posts])
            offset += step
            print('offset {}'.format(offset))

    def update_discuz_post(self, post_id):
        if post_id:
            return self.get_post(post_id)
        return None

    def get_posts_list(self, fid, start_page, end_page, filter='digest', orderby='dateline'):
        print('分类 {}, {} 页 到 {} 页'.format(fid, start_page, end_page))
        posts_need_detail = app.run_futures(
            [self.discuz.request_thread(fid, page, filter, orderby) for page in range(start_page, end_page + 1)],
            repository.PostRepo.save_posts)

        return posts_need_detail

    def get_posts(self, posts):
        if posts is not None:
            details = app.run_futures([self.discuz.request_post(post['post_id']) for post in posts],
                                      repository.PostRepo.save_post_detail)
            return details

    def get_post(self, tid):
        detail = app.run_futures([self.discuz.request_post(tid)], repository.PostRepo.save_post_detail)
        return detail


def temp_test(crawler):
    posts_list = crawler.get_posts_list(19, 1, 2)
    # app.logger().info(posts_list)
    exit(1)


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

    debug = bool(app.get_config('APP', 'debug') == 1)

    crawler = DiscuzCrawler(int(app.get_config('APP', 'concur')), debug)

    if args.get('post', None):
        crawler.update_discuz_post(post_id=args['post'])
        exit()

    if args.get('update'):
        crawler.update_detail_from_database()
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
    crawler.update_discuz(fids, with_detail)
