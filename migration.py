from peewee import *
import datetime


class BaseModel(Model):
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

    def dicts(self):
        r = {}
        for k in self._data.keys():
            r[k] = getattr(self, k)
        return r

    @classmethod
    def first_or_create(cls, check_attr, new_attr=None):
        try:
            if check_attr is None:
                return None

            model = cls.get(getattr(cls, cls.primary_key()) == check_attr.get(cls.primary_key()))
            # print('{} exist, skip'.format(video_info['view_id']))
        except cls.DoesNotExist:
            if new_attr is not None:
                check_attr.update(new_attr)
            model = cls.create(**check_attr)
            # print('save {}, success'.format(video_info['view_id']))

        return model


class FromPost(BaseModel):
    class Meta:
        database = MySQLDatabase('easy91-forum', user='root', host='127.0.0.1', password='secret', port=3306)
        db_table = 'tmp_post'

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


class ToPost(BaseModel):
    class Meta:
        database = MySQLDatabase('easy91-forum', user='root', host='127.0.0.1', password='secret', port=3306)
        db_table = 'post'

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


if __name__ == '__main__':
    offset = 0
    limit = 200
    posts = FromPost.select().offset(offset).limit(limit)
    while posts.count() > 0:
        for post in posts:
            try:
                remote_post = ToPost.get(ToPost.post_id == post['post_id'])
                print('{} exist, skip'.format(post['post_id']))
            except ToPost.DoesNotExist:

                remote_post = ToPost.create(
                    **{'post_id': post['post_id'], 'title': post['title'], 'content': post['content'],
                       'desc': post['desc'], 'photos': post['photos'], 'post_time': post['post_time'],
                       'author_name': post['author_name'], 'author_id': post['author_id'], 'forum_id': post['forum_id'],
                       'digest': post['digest']})
                print('save {}, success'.format(post['post_id']))
    posts = FromPost.select().offset(offset).limit(limit)
