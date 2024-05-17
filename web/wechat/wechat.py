import json

from flask import Blueprint, request, current_app, abort

from web import siwa
from web.wechat.service import check_token, send_alert

bp = Blueprint('wechat', __name__, url_prefix='/wechat')


@bp.route('/hook/<env>', methods=['GET', 'POST'])
@siwa.doc()
def send_to_env(env):
    """
    处理来自Prometheus Alert manager的报警通知。

    参数:
    - env: 报警环境，用于选择相应的机器人令牌和密钥。

    返回值:
    - 根据请求方法返回不同的响应，GET请求返回欢迎信息，POST请求处理报警通知并返回成功信息。
    """
    if request.method == 'POST':
        check_token(env)
        try:
            post_data = request.get_data()
            data = json.loads(post_data)
        except json.JSONDecodeError:
            abort(400, "Invalid JSON payload")
        current_app.logger.debug(post_data)
        send_alert(env, data)
        return 'Success', 200
    else:
        return check_token(env)
