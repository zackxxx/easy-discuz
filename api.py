from aiohttp import web
import asyncio
import urllib
import sys
import os
import aiohttp_cors

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))

import app
import repository

# from playhouse.flask_utils import PaginatedQuery
# Add the directory containing your module to the Python path (wants absolute paths)


crawler = init_crawler(debug=False)


async def docs(request):
    data = {
        '列表': {
            'route': '/',
            'params': {
                'cat': {
                    'rf': '最近加精',
                    'top': '本月最热',
                    'hot': '当前最热',
                    'md': '本月讨论',
                    'rp': '最近得分',
                    'tf': '本月收藏',
                    'mf': ' 收藏最多',
                    'long': '10分钟以上 ',
                },
                'page': 'int',
                'm': 'int(当cat为top)，取值为(1-12,-1=last_month)'
            },
        },
        '详情': {
            'route': 'detail/{view_id}',
        },
        '用户': {
            'route': 'user/{user_no}',
            'params': {
                'page': 'int',
            }
        }
    }
    return web.json_response(data)


async def fetch_all_video(request):
    counter = 0
    start = request.rel_url.query.get('start', 1)
    end = request.rel_url.query.get('end', 20)

    todo_iter = asyncio.as_completed([crawler.api.get_posts_list(page=i) for i in range(int(start), int(end))])
    for future in todo_iter:
        res = await future
        for view_id, video_info in res.items():
            persist_video_source(video_info)
            counter += 1
    print('update count {}'.format(counter))
    return counter


async def sync(request):
    asyncio.ensure_future(fetch_all_video(request))
    return web.json_response({'data': 'ok'})


async def search(request):
    meta = {}
    data = {}
    per_page = int(request.rel_url.query.get('per_page', 20))
    page = int(request.rel_url.query.get('page', 1))
    keyword = request.rel_url.query.get('keyword', None)
    if keyword is None:
        data, meta['pagination'] = await crawler.api.get_posts_list(with_meta=True)
    else:
        video_query = VideoSource.select().orwhere(VideoSource.title.contains(keyword)).orwhere(
            VideoSource.user_name.contains(keyword))

        try:
            data = {video_info.view_id: video_info.dicts() for video_info in video_query.paginate(page, per_page)}
        except VideoSource.DoesNotExist:
            pass
        total_count = video_query.count()
        meta['pagination'] = {
            'last_page': total_count // per_page,
            'current_page': page,
            'per_page': per_page,
            'page_items_count': len(data),
        }

    return web.json_response({'data': data, 'meta': meta})


async def lists(request):
    meta = {
        'cat': {
            'rf': '最近加精',
            'top': '本月最热',
            'hot': '当前最热',
            'md': '本月讨论',
            'rp': '最近得分',
            'tf': '本月收藏',
            'mf': ' 收藏最多',
            'long': '10分钟以上 ',
        }
    }

    cat = request.rel_url.query.get('cat', None)
    page = request.rel_url.query.get('page', 0)
    extra = {}

    if cat == 'top':
        extra['m'] = request.rel_url.query.get('m', 0)

    data, meta['pagination'] = await crawler.api.get_posts_list(cat, page, with_meta=True, extra=extra)
    return web.json_response({'data': data, 'meta': meta})


async def user(request):
    meta = {}
    data = {}
    user_no = request.match_info.get('user_no', None)
    if user is not None:
        page = request.rel_url.query.get('page', 1)
        data, meta['pagination'] = await crawler.api.get_user_lists(user_no, page, with_meta=True)

    return web.json_response({'data': data, 'meta': meta})


async def detail(request):
    try:
        data = {}
        if request.method == 'POST':
            data = await request.post()
            url = data.get('url')
            if 'http' in url:
                print('view url {}'.format(url))
                params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                view_ids = params.get('viewkey')
                view_id = view_ids[0]
            else:
                view_id = url
        else:
            view_id = request.match_info.get('view_id', None)
        if view_id:
            data = await crawler.api.get_post(view_id)
    except Exception as e:
        print(e)
    finally:
        return web.json_response({'data': data})


if __name__ == '__main__':
    if len(sys.argv) == 1:
        port = 8081
    else:
        port = int(sys.argv[-1])

    app = web.Application()

    app.router.add_get('/', lists)
    app.router.add_get('/user/{user_no}', user)
    app.router.add_get('/detail/{view_id}', detail)
    app.router.add_get('/docs', docs)
    app.router.add_get('/sync', sync)
    app.router.add_get('/search', search)

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)

    web.run_app(app, port=port)
