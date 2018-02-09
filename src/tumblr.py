import json
import tumblpy
import threading
# import multiprocessing
# import multiprocessing.pool
import argparse

from library import helper
from src.repository import Post


class TumblrLimitException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


def tumblr_posting(client, discuz_post, my_blog):
    try:
        if discuz_post is None:
            return None

        post = {
            'type': 'text',
            'native_inline_images': True,
            'title': discuz_post['title'],
            'body': discuz_post['desc'],
            'tags': discuz_post['author_name'],
        }
        res = client.post('post', my_blog, params=post)
    except tumblpy.exceptions.TumblpyError as e:
        if ('your daily post limit' in str(e)):
            raise TumblrLimitException(str(e))
        else:
            print(e)
            print('reblog fail: {}'.format(discuz_post['post_id']))
            Post.update(downloaded=2).where(Post.post_id == discuz_post['post_id']).execute()
    else:
        print('reblog success: {}'.format(res))
        Post.update(downloaded=1).where(Post.post_id == discuz_post['post_id']).execute()


def init_client():
    return tumblpy.Tumblpy(helper.get_config('TUMBLR', 'consumer_key'), helper.get_config('TUMBLR', 'consumer_secret'),
                           helper.get_config('TUMBLR', 'token'), helper.get_config('TUMBLR', 'token_secret'))


def reblog(status=0, total=1000, fid=None):
    client = init_client()
    offset = 0
    step = 200
    if total < step:
        step = total
    while total >= offset:
        query = Post.select().where(Post.downloaded == status).where(Post.digest == 1).order_by(Post.id.desc())
        if fid:
            query = query.where(Post.forum_id == fid)
        posts = query.limit(step)

        if posts.count() > 0:
            print('start count {}'.format(len(posts)))
            # pool = multiprocessing.pool.ThreadPool(20)
            # m = multiprocessing.Manager()
            # event = m.Event()
            sem = threading.BoundedSemaphore(20)
            for post in posts:
                sem.acquire()
                t = threading.Thread(target=reblog_a_blog, args=(client, post, sem))
                t.start()
                # pool.apply_async(reblog_a_blog, args=(client, post))
            # pool.close()
            # pool.join()
            offset += len(posts)
            print('finish reblog {}'.format(offset))
        else:
            print('no post')
            break


def reblog_a_blog(client, post, sem):
    try:
        print('reblog start {}'.format(post.post_id))

        if post.photos is None:
            print('skip, blog {} has no detail'.format(post['post_id']))
            return None

        post = {
            'post_id': post.post_id,
            'title': post.title,
            'desc': post.desc,
            'author_name': post.author_name,
            'photos': json.loads(post.photos),
        }
        format_post = format_discuz_post(post)
        if format_post is None:
            print('skip reblog {}'.format(post['post_id']))
            return None

        for num, desc in enumerate(format_post['contents']):
            reblog_post = dict(post)
            reblog_post['desc'] = desc
            if len(format_post['contents']) > 1:
                reblog_post['title'] += '【{}】'.format(num + 1)
            tumblr_posting(client, reblog_post, helper.get_config('TUMBLR', 'blog_name'))
    except TumblrLimitException as e:
        print(e)
    except Exception as e:
        print(e)
        print('reblog fail for {}'.format(post['post_id']))
        return 'end'
    finally:
        sem.release()


def format_discuz_post(post):
    image_count = 0
    image_total = len(post['photos'])
    if image_total < 5:
        Post.update(downloaded=3).where(Post.post_id == post['post_id']).execute()
        return None
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
        *('<img src="{}">'.format(helper.get_config('DISCUZ', 'base_url') + 'attachments/%s' % photo_id) for photo_id in
          post['photos']))
    post['contents'] = post['desc'].split(split_name)
    return post


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--total', type=int, default=200, help='total reblog count')
    parser.add_argument('-f', '--forum', help='forum id')
    parser.add_argument('-s', '--status', type=int, default=0, help='blog status, 0: not reblog, 1: succeed, 2: fail')
    args = vars(parser.parse_args())

    reblog(status=args.get('status'), total=args.get('total'), fid=args.get('forum'))
