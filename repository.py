import app
from peewee import *
import datetime
import json


class BaseModel(Model):
    class Meta:
        database = app.init_db()

    @classmethod
    def get_or_none(cls, **kwargs):
        try:
            model = cls.get(**kwargs)
        except cls.DoesNotExist:
            return None
        else:
            return model

    @classmethod
    def primary_key(cls):
        return 'id'

    def __getitem__(self, item):
        return getattr(self, item)

    def __str__(self):
        return json.dumps(self.dicts())

    def dicts(self):
        r = {}
        for k in self._data.keys():
            r[k] = getattr(self, k)
        return r

    @classmethod
    def first_or_create(cls, check_attr, new_attr=None):
        if new_attr is None:
            return cls.get_or_create(cls, **check_attr)

        model = cls.get_or_none(**check_attr)
        if model is None:
            check_attr.update(new_attr)
            model = cls.create(**check_attr)

        return model


class Post(BaseModel):
    id = IntegerField(primary_key=True)
    post_id = CharField(null=True, unique=True)
    title = CharField(null=True, default=0)
    content = TextField(null=True)
    desc = TextField(null=True)
    photos = TextField(null=True)
    post_time = CharField(null=True)
    author_name = CharField(null=True)
    author_id = CharField(null=True)
    forum_id = CharField(null=True)
    downloaded = IntegerField(default=0)
    digest = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    @classmethod
    def primary_key(cls):
        return 'post_id'

    @classmethod
    def primary_key(cls):
        return 'post_id'


class PostRepo(object):
    @staticmethod
    def get_need_detail(limit=100, offset=0):
        return Post.select().where(Post.photos >> None).offset(offset).limit(limit)

    @staticmethod
    def save_posts(thread_items):
        if not thread_items or len(thread_items) <= 0:
            return None

        post_exist = 0
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
                post_exist += 1
                if not post.photos:
                    items_need_detail.append(item)
        print('Exist digest count {}, Need detail posts count {}'.format(post_exist, len(items_need_detail)))
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


Post.create_table(True)
