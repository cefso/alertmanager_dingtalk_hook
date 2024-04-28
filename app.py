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
    # 获取external url
    global EXTERNAL_URL
    if not EXTERNAL_URL:
        EXTERNAL_URL = data['externalURL']

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

    # 提取状态信息和报警列表
    status = data.get('status')
    alerts = data.get('alerts', [])
    alert_dict = {}

    # 遍历每个报警，组织按报警名分组
    for alert in alerts:
        try:
            alert_name = alert['labels'].get('alertname')
        except KeyError as e:
            app.logger.error("Warning: Alert missing 'labels' or 'labels' missing 'alertname'. Skipping alert.")
            continue

        if alert_name is not None:
            alert_dict.setdefault(alert_name, []).append(alert)

    # 为每组报警生成markdown格式的消息
    for alert_name, alerts_group in alert_dict.items():
        alert_number = len(alerts_group)
        title_firing = '**[%s]** 有 **%d** 条新的报警' % (alert_name, alert_number)
        title_resolved = '**[%s]** 有 **%d** 条报警已经恢复' % (alert_name, alert_number)
        # 生成报警列表的markdown文本，只包含前5条
        alert_list = ''.join(_mark_item(alert) for alert in alerts_group[:5])

        # 组装完整的markdown消息
        if status == 'firing':
            markdown_text = f"![](https://teamo-md.oss-cn-shanghai.aliyuncs.com/pod.png)\n{title_firing}\n{alert_list}\n[点击查看完整信息]({EXTERNAL_URL})"
            send_data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title_firing,
                    "text": markdown_text
                }
            }
        else:
            markdown_text = f"![](https://teamo-md.oss-cn-shanghai.aliyuncs.com/pod.png)\n{title_resolved}\n{alert_list}\n[点击查看完整信息]({EXTERNAL_URL})"
            send_data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title_resolved,
                    "text": markdown_text
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
        app.logger.error(f"缺少必要的键: {e}", exc_info=True)
        return "处理报警信息时发生错误"
    except ValueError as e:
        app.logger.error(f"数据类型错误: {e}", exc_info=True)
        return "处理报警信息时发生错误"

    annotations = f"> 总结: {summary}\n\n> 描述: {description}"

    if 'job' in labels:
        mark_item = f"\n> job: {labels['job']}\n\n{annotations}\n---\n"
    else:
        mark_item = annotations + '\n'

    return mark_item


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


def check_token(env):
    try:
        # 通过os.getenv获取环境变量，考虑到敏感信息访问的安全性，此处保持不变
        token = os.getenv('ROBOT_TOKEN_' + env.upper())
        secret = os.getenv('ROBOT_SECRET_' + env.upper())

        if token is None or secret is None:
            # 当环境变量未设置时，使用400状态码反映Bad Request的情况
            return f'Welcome to use Prometheus Alert manager Dingtalk webhook server! This URL is for {env.upper()} environment. But env not set!', 400
        else:
            # 环境变量设置正确，返回成功信息
            return f'Welcome to use Prometheus Alert manager Dingtalk webhook server! This URL is for {env.upper()} environment.', 200
    except ValueError as ve:
        # 对于输入验证引发的异常，返回400状态码
        app.logger.error(f"Input validation error: {ve}")
        return f'Invalid input: {ve}', 400
    except Exception as e:
        # 对于预期内的其他异常，记录详细错误日志，并返回500状态码
        app.logger.error(f"An error occurred: {e}")
        return f'Welcome to use Prometheus Alert manager Dingtalk webhook server! We found an error for {env.upper()} environment: {e}', 500


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
        check_token(env)
        try:
            post_data = request.get_data()
            data = json.loads(post_data)
        except json.JSONDecodeError:
            abort(400, "Invalid JSON payload")
        app.logger.debug(post_data)
        send_alert(env, data)
        return 'Success', 200
    else:
        return check_token(env)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
