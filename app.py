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

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('LOG_LEVEL') == 'debug' else logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s')

# Environment variables
ROBOT_TOKEN_PRE = os.getenv('ROBOT_TOKEN_PRE')
ROBOT_SECRET_PRE = os.getenv('ROBOT_SECRET_PRE')
ROBOT_TOKEN_PRO = os.getenv('ROBOT_TOKEN_PRO')
ROBOT_SECRET_PRO = os.getenv('ROBOT_SECRET_PRO')


# Helper functions
def send_alert(env, data):
    """
    发送报警通知到钉钉

    参数:
    - env: 报警环境，用于确定使用哪个环境的token和secret（如'pre'表示预发环境，'pro'表示生产环境）
    - data: 包含报警状态和详细信息的数据字典

    返回值:
    - 无
    """
    # 根据环境获取token和secret
    token, secret = get_token_and_secret(env)
    # 根据不同的环境覆盖token和secret
    if env == 'pre':
        token = os.getenv('ROBOT_TOKEN_PRE')
        secret = os.getenv('ROBOT_SECRET_PRE')
    elif env == 'pro':
        token = os.getenv('ROBOT_TOKEN_PRO')
        secret = os.getenv('ROBOT_SECRET_PRO')
    else:
        # 如果环境不是预发或生产，则清空token和secret
        token = ''
        secret = ''
    # 检查token和secret是否设置
    if not token:
        app.logger.error('you must set ROBOT_TOKEN env')
        return
    if not secret:
        app.logger.error('you must set ROBOT_SECRET env')
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
        external_url = 'http://vmalert.fastfish.com'
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
                "text": "{0}\n![](https://teamo-md.oss-cn-shanghai.aliyuncs.com/pod.png)\n{1}\n[点击查看完整信息]({2})\n".format(
                    title, alert_list, external_url)
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
    - alert: 单个报警的数据字典

    返回值:
    - 格式化后的markdown字符串
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
        print(f"缺少必要的键: {e}")
        return ""
    except ValueError as e:
        print(e)
        return ""

    # 构造markdown格式的报警信息
    annotations = f"> 总结: {summary}\n\n> 描述: {description}"

    mark_item = ""
    if 'job' in labels:
        mark_item = f"\n> job: {labels['job']}\n\n{annotations}\n---\n"
    else:
        mark_item = annotations + '\n'

    return mark_item


def get_token_and_secret(env):
    """
    根据指定的环境获取相应的机器人令牌和密钥。

    参数:
    - env: 字符串，指定环境，可以是'pre'（预发布环境）或'pro'（生产环境）。

    返回值:
    - tuple: 包含机器人令牌和密钥的元组。若env为'pre'，返回ROBOT_TOKEN_PRE和ROBOT_SECRET_PRE；
             若env为'pro'，返回ROBOT_TOKEN_PRO和ROBOT_SECRET_PRO。

    异常:
    - 如果指定的环境无效，会引发一个400错误，错误信息为"Invalid environment specified"。
    """
    if env == 'pre':
        return ROBOT_TOKEN_PRE, ROBOT_SECRET_PRE
    elif env == 'pro':
        return ROBOT_TOKEN_PRO, ROBOT_SECRET_PRO
    else:
        # 对于无效的环境参数，触发HTTP 400错误
        abort(400, "Invalid environment specified")


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
    处理根路径的GET请求，返回欢迎信息。

    参数:
    无

    返回值:
    str: 返回一个欢迎使用的字符串信息。
    """
    if request.method == 'GET':  # 判断请求方法是否为GET
        return 'weclome to use prometheus alertmanager dingtalk webhook server!'


@app.route('/<env>', methods=['GET', 'POST'])
def send_to_env(env):
    """
    根据请求的方法，将数据发送到指定的环境。

    :param env: 指定的目标环境，URL路径参数。
    :return: 根据请求方法的不同，返回不同的响应。POST请求成功返回'Success'和状态码200，
             GET请求返回欢迎信息和状态码200。
    """
    if request.method == 'POST':
        # 尝试获取并解析POST请求的数据
        post_data = request.get_data()
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            # 如果JSON解析失败，返回400错误
            abort(400, "Invalid JSON payload")

        # 记录POST数据的调试信息
        app.logger.debug(post_data)
        # 发送警报到指定环境
        send_alert(env, data)
        return 'Success', 200
    else:
        # 对于GET请求，返回欢迎信息
        return f'Welcome to use Prometheus Alertmanager Dingtalk webhook server! This URL is for {env.upper()} environment.', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
