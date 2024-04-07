import os
import json
import logging
import requests
import time
import hmac
import hashlib
import base64
import urllib.parse

from flask import Flask
from flask import request

app = Flask(__name__)

logging.basicConfig(
    level=logging.DEBUG if os.getenv('LOG_LEVEL') == 'debug' else logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s')


@app.route('/', methods=['GET'])
def hello():
    if request.method == 'GET':
        return 'weclome to use prometheus alertmanager dingtalk webhook server!'


@app.route('/pre', methods=['GET', 'POST'])
def send_pre():
    if request.method == 'POST':
        post_data = request.get_data()
        app.logger.debug(post_data)
        send_alert('pre', json.loads(post_data))
        return 'success'
    else:
        return 'weclome to use prometheus alertmanager dingtalk webhook server! this url alert while send to pre robot'


@app.route('/pro', methods=['GET', 'POST'])
def send_pro():
    if request.method == 'POST':
        post_data = request.get_data()
        app.logger.debug(post_data)
        send_alert('pro', json.loads(post_data))
        return 'success'
    else:
        return 'weclome to use prometheus alertmanager dingtalk webhook server! this url alert while send to pro robot'


def send_alert(env, data):
    if env == 'pre':
        token = os.getenv('ROBOT_TOKEN_PRE')
        secret = os.getenv('ROBOT_SECRET_PRE')
    elif env == 'pro':
        token = os.getenv('ROBOT_TOKEN_PRO')
        secret = os.getenv('ROBOT_SECRET_PRO')
    else:
        token = ''
        secret = ''
    if not token:
        app.logger.error('you must set ROBOT_TOKEN env')
        return
    if not secret:
        app.logger.error('you must set ROBOT_SECRET env')
        return
    timestamp = int(round(time.time() * 1000))
    url = 'https://oapi.dingtalk.com/robot/send?access_token=%s&timestamp=%d&sign=%s' % (
        token, timestamp, make_sign(timestamp, secret))

    status = data['status']
    alerts = data['alerts']
    alert_name = alerts[0]['labels']['alertname']

    def _mark_item(alert):
        labels = alert['labels']
        annotations = "> 总结: {} \n\n > 描述: {}".format(alert['annotations']['summary'],
                                                                    alert['annotations']['description'])
        if 'job' in labels:
            mark_item = "\n> job: " + labels['job'] + '\n\n' + annotations + '\n' + '---' + '\n'
        else:
            mark_item = annotations + '\n'
        return mark_item

    if status == 'resolved':  # 告警恢复
        send_data = {
            "msgtype": "text",
            "text": {
                "content": "报警 %s 已恢复" % alert_name
            }
        }
    else:
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

    req = requests.post(url, json=send_data)
    result = req.json()
    if result['errcode'] != 0:
        app.logger.error('notify dingtalk error: %s' % result['errcode'])


def make_sign(timestamp, secret):
    """新版钉钉更新了安全策略，这里我们采用签名的方式进行安全认证
    https://ding-doc.dingtalk.com/doc#/serverapi2/qf2nxq
    """
    secret_enc = bytes(secret, 'utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = bytes(string_to_sign, 'utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return sign


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
