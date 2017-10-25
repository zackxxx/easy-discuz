from aiohttp import web
import asyncio
import sys
import aiohttp_cors

import app
from discuz import Discuz
import repository
import json

# from playhouse.flask_utils import PaginatedQuery
# Add the directory containing your module to the Python path (wants absolute paths)

discuz = Discuz(concur_req=10, debug=False)


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


async def sync(request):
    fid = request.rel_url.query.get('fid', 19)
    start = request.rel_url.query.get('start', 1)
    end = request.rel_url.query.get('end', 5)
    post_filter = request.rel_url.query.get('filter', None)
    asyncio.ensure_future(
        app.futures([discuz.request_thread(fid, page, post_filter) for page in range(int(start), int(end))]))
    return web.json_response({'data': 'ok'})


async def search(request):
    meta = {}
    per_page = int(request.rel_url.query.get('per_page', 20))
    page = int(request.rel_url.query.get('page', 1))
    keyword = request.rel_url.query.get('keyword', None)

    if keyword is None:
        data = await discuz.request_thread(19)
    else:
        data, total_count = repository.PostRepo.search(keyword, page, per_page)
        meta['pagination'] = {
            'page_count': len(data),
            'total_count': total_count,
            'last_page': total_count // per_page + 1,
            'current_page': page,
            'per_page': per_page,
        }

    return web.json_response({'data': json.loads(json.dumps(data, default=lambda x: None)), 'meta': meta})


async def post(request):
    try:
        data = {}
        post_id = request.match_info.get('post_id', None)
        if post_id:
            data = await discuz.request_post(post_id)
    except Exception as e:
        print('error for post {}'.format(post_id))
        print(e)
    finally:
        return web.json_response({'data': json.loads(json.dumps(data, default=lambda x: None))})


async def posts_index(request):
    fid = request.rel_url.query.get('fid', 19)
    page = request.rel_url.query.get('page', 1)
    post_filter = request.rel_url.query.get('filter', None)
    data = await discuz.request_thread(fid, page, post_filter)
    return web.json_response({'data': data})


if __name__ == '__main__':
    if len(sys.argv) == 1:
        port = 8081
    else:
        port = int(sys.argv[-1])

    app = web.Application()

    app.router.add_get('/', posts_index)
    app.router.add_get('/posts/{post_id}', post)
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
