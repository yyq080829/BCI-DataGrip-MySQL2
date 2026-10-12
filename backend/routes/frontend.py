"""
前端静态文件托管（让 `python app.py` 也能直接打开前端页面）

背景：
  前端队友把问卷系统(HTML)和 Unity WebGL 入口放在项目根目录的 /frontend 文件夹。
  但 backend 原本只提供 /api 接口，不托管静态文件，所以“启动 app.py 打不开前端”。
  这里用 Flask 把 /frontend 作为静态资源目录托管起来，访问 `/` 即可打开问卷系统。

新手注意：
  · 前端页面用绝对地址 http://127.0.0.1:5000/api/... 调接口，和后端同源(同端口)，
    因此无需额外跨域(CORS)配置。
  · `/` 默认指向问卷页 `康游智创(5).html`；Unity WebGL 入口为 `/index.html`
    （需 /frontend/Build 下的资源，当前可能缺失）。
  · /api、/monitor、/unity 等接口由各自蓝图处理，不会误入本静态路由。
"""

import os
from flask import Blueprint, send_from_directory, abort

# 计算 frontend 目录绝对路径：backend/routes/frontend.py -> ../../frontend
_FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')
)

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route('/')
def index():
    """根路径 `/`：打开问卷系统页面（若文件缺失则回退到 index.html）。"""
    entry = '康游智创(5).html'
    if not os.path.isfile(os.path.join(_FRONTEND_DIR, entry)):
        entry = 'index.html'
    return send_from_directory(_FRONTEND_DIR, entry)


@frontend_bp.route('/<path:filename>')
def static_file(filename):
    """托管 /frontend 下任意静态文件（html/js/css/图片等）。

    例如：/index.html -> Unity WebGL 入口；/images/xxx.jpg -> 图片资源。
    已做目录穿越防护（拦截 '../ ' 与绝对路径）。
    """
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        abort(404)
    full_path = os.path.join(_FRONTEND_DIR, filename)
    if not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(_FRONTEND_DIR, filename)
