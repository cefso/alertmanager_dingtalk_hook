import base64
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse

import requests
from flask import Flask, abort
from flask import request

app = Flask(__name__)

# 设置日志记录级别
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')

# 环境变量配置
# ROBOT_TOKENS = {'pro': os.getenv('ROBOT_TOKEN_PRO')}
# ROBOT_SECRETS = {'pro': os.getenv('ROBOT_SECRET_PRO')}
EXTERNAL_URL = os.getenv('EXTERNAL_URL', '')

# 错误消息和常量定义
ERROR_TOKEN_NOT_SET = 'you must set ROBOT_TOKEN env'
ERROR_SECRET_NOT_SET = 'you must set ROBOT_SECRET env'


# Helper functions

def send_alert(env, data):
    """
    发送报警通知到钉钉

    参数:
    - env: 报警环境，用于选择相应的机器人令牌和密钥。
    - data: 包含报警信息的字典。

    无返回值。
    """
    # 根据环境获取token和secret
    # token = ROBOT_TOKENS.get(env, '')
    # secret = ROBOT_SECRETS.get(env, '')
    token = os.getenv('ROBOT_TOKEN_' + env.upper())
    secret = os.getenv('ROBOT_SECRET_' + env.upper())

    if not token:
        app.logger.error(ERROR_TOKEN_NOT_SET)
        return
    if not secret:
        app.logger.error(ERROR_SECRET_NOT_SET)
        return

    # 构造钉钉消息的URL
    timestamp = int(round(time.time() * 1000))
    url = 'https://oapi.dingtalk.com/robot/send?access_token=%s&timestamp=%d&sign=%s' % (
        token, timestamp, make_sign(timestamp, secret))

    # 解析报警数据
    status = data['status']
    alerts = data['alerts']
    alert_name = alerts[0]['labels']['alertname']

    # 根据报警状态构造发送的消息
    if status == 'resolved':  # 如果报警恢复
        send_data = {
            "msgtype": "text",
            "text": {
                "content": "报警 %s 已恢复" % alert_name
            }
        }
    else:
        # 构造报警通知的markdown格式内容
        title = '**[%s]** 有 **%d** 条新的报警' % (alert_name, len(alerts))

        alert_list = ''
        if len(alerts) <= 5:
            for i in range(len(alerts)):
                alert_list += _mark_item(alerts[i])
        else:
            for i in range(5):
                alert_list += _mark_item(alerts[i])
        send_data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"{title}\n![](https://teamo-md.oss-cn-shanghai.aliyuncs.com/pod.png)\n{alert_list}\n[点击查看完整信息]({EXTERNAL_URL})"
            }
        }

    # 发送消息到钉钉
    req = requests.post(url, json=send_data)
    result = req.json()
    # 检查发送结果
    if result['errcode'] != 0:
        app.logger.error('notify dingtalk error: %s' % result['errcode'])


def _mark_item(alert):
    """
    格式化单个报警项的信息为markdown格式

    参数:
    - alert: 包含单个报警信息的字典。

    返回值:
    - 格式化后的markdown字符串。
    """
    try:
        labels = alert.get('labels', {})
        annotations_data = alert.get('annotations', {})
        # 确保 'summary' 和 'description' 是字符串类型
        summary = annotations_data.get('summary', '').strip()
        description = annotations_data.get('description', '').strip()
        if not isinstance(summary, str) or not isinstance(description, str):
            raise ValueError("summary和description必须是字符串类型")
    except KeyError as e:
        app.logger.error(f"缺少必要的键: {e}")
        return ""
    except ValueError as e:
        app.logger.error(e)
        return ""

    # 构造markdown格式的报警信息
    annotations = f"> 总结: {summary}\n\n> 描述: {description}"

    if 'job' in labels:
        mark_item = f"\n> job: {labels['job']}\n\n{annotations}\n---\n"
    else:
        mark_item = annotations + '\n'

    return mark_item


# def get_token_and_secret(env):
#     """
#     根据指定的环境获取相应的机器人令牌和密钥。
#
#     参数:
#     - env: 字符串，指定环境，可以是'pre'（预发布环境）或'pro'（生产环境）。
#
#     返回值:
#     - tuple: 包含机器人令牌和密钥的元组。若env为'pre'，返回ROBOT_TOKEN_PRE和ROBOT_SECRET_PRE；
#              若env为'pro'，返回ROBOT_TOKEN_PRO和ROBOT_SECRET_PRO。
#
#     异常:
#     - 如果指定的环境无效，会引发一个400错误，错误信息为"Invalid environment specified"。
#     """
#     if env == 'pre':
#         return ROBOT_TOKEN_PRE, ROBOT_SECRET_PRE
#     elif env == 'pro':
#         return ROBOT_TOKEN_PRO, ROBOT_SECRET_PRO
#     else:
#         # 对于无效的环境参数，触发HTTP 400错误
#         abort(400, "Invalid environment specified")


def make_sign(timestamp, secret):
    """
    生成钉钉安全签名。

    新版钉钉更新了安全策略，这里我们采用签名的方式进行安全认证。
    具体文档参考：https://ding-doc.dingtalk.com/doc#/serverapi2/qf2nxq

    参数:
    - timestamp: 时间戳，用于签名的字符串。
    - secret: 私钥，用于签名的密钥。

    返回值:
    - sign: 生成的签名字符串。
    """

    # 将密钥转换为字节串
    secret_enc = bytes(secret, 'utf-8')

    # 构建待签名字符串
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = bytes(string_to_sign, 'utf-8')

    # 使用HMAC-SHA256算法计算签名
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()

    # 对签名结果进行Base64编码，并使用URL安全方式编码
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

    return sign


@app.route('/', methods=['GET'])
def hello():
    """
    首页路由，返回欢迎信息。
    """
    return 'welcome to use prometheus alert manager dingtalk webhook server!'


@app.route('/hook/<env>', methods=['GET', 'POST'])
def send_to_env(env):
    """
    处理来自Prometheus Alert manager的报警通知。

    参数:
    - env: 报警环境，用于选择相应的机器人令牌和密钥。

    返回值:
    - 根据请求方法返回不同的响应，GET请求返回欢迎信息，POST请求处理报警通知并返回成功信息。
    """
    if request.method == 'POST':
        try:
            post_data = request.get_data()
            data = json.loads(post_data)
        except json.JSONDecodeError:
            abort(400, "Invalid JSON payload")
        app.logger.debug(post_data)
        send_alert(env, data)
        return 'Success', 200
    else:
        return f'Welcome to use Prometheus Alert manager Dingtalk webhook server! This URL is for {env.upper()} environment.', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
