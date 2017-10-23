import sys
from common import dd, get_config
import json
import tumblpy
import multiprocessing
import os

from discuz import Discuz
from repository import Post
import argparse


def init_discuz(debug=False):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json'), 'r') as f:
        cookies = json.loads(f.read())

    discuz = Discuz(concur_req=int(get_config('APP', 'concur')))
    discuz.set_cookies(cookies)
    return discuz


def update_discuz(discuz, fids, with_detail=True):
    for fid_info in fids:
        if fid_info[0] in [19, 21]:
            discuz.set_cookies({})
        threads_posts = discuz.get_lists(*fid_info)
        if with_detail:
            for posts in threads_posts:
                discuz.get_posts_detail(posts)


def update_detail_from_database(discuz):
    step = 100
    offset = 0
    while True:
        posts = Post.select().where(Post.photos >> None).limit(step)
        if posts.count() == 0:
            break

        discuz.get_posts_detail(posts)
        print([post['post_id'] for post in posts])
        offset += step
        print('offset {}'.format(offset))


def update_discuz_post(discuz, post_id):
    if post_id:
        post = discuz.get_detail(post_id)


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

    debug = bool(get_config('APP', 'debug') == 1)

    discuz = init_discuz(debug=debug)

    if args.get('post', None):
        update_discuz_post(discuz, post_id=args['post'])
        exit()

    if args.get('update'):
        update_detail_from_database(discuz)
        exit()

    if args.get('forum'):
        filter_type = args.get('filter', 'digest')
        if filter_type == 'all':
            filter_type = ''
        fids = [
            (args['forum'], args.get('start'), args.get('end'), filter_type),
        ]
    else:
        fids = [
            (19, 1, 5),
            (21, 1, 5),
        ]

    with_detail = args['detail']
    update_discuz(discuz, fids, with_detail)
