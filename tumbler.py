import json
import tumblpy
import multiprocessing
import os

from common import dd, get_config
from repository import Post


class TumblrLimitException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


def tumblr_posting(client, discuz_post, my_blog):
    try:
        if discuz_post is None:
            return None

        print('reblog start {}'.format(discuz_post['post_id']))
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
    return tumblpy.Tumblpy(get_config('TUMBLR', 'consumer_key'), get_config('TUMBLR', 'consumer_secret'),
                           get_config('TUMBLR', 'token'), get_config('TUMBLR', 'token_secret'))


def reblog(status=0):
    client = init_client()
    offset = 0
    step = 200
    posts = Post.select().where(Post.downloaded == status).order_by(Post.id.desc()).offset(offset).limit(step)
    if posts.count() > 0:
        print('start count {}'.format(len(posts)))
        pool = multiprocessing.Pool(multiprocessing.cpu_count())
        m = multiprocessing.Manager()
        event = m.Event()
        for post in posts:
            pool.apply_async(reblog_a_blog, (client, post, event))
        pool.close()
        pool.join()
        pool.terminate()
    else:
        print('no post')


def reblog_a_blog(client, post):
    try:
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
            tumblr_posting(client, reblog_post, get_config('TUMBLR', 'blog_name'))
    except TumblrLimitException as e:
        print(e)
    except Exception as e:
        print(e)


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
        *('<img src="{}">'.format(get_config('DISCUZ', 'base_url') + 'attachments/%s' % photo_id) for photo_id in
          post['photos']))
    post['contents'] = post['desc'].split(split_name)
    return post


if __name__ == '__main__':
    reblog()