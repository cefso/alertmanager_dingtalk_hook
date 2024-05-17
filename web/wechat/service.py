from flask import current_app
import os
import time

import requests

# 环境变量配置
EXTERNAL_URL = os.getenv('EXTERNAL_URL', '')

# 错误消息和常量定义
ERROR_KEY_NOT_SET = 'you must set ROBOT_KEY env'


# Helper functions

def send_alert(env, data):
    """
    发送报警通知到钉钉

    参数:
    - env: 报警环境，用于选择相应的机器人令牌和密钥。
    - data: 包含报警信息的字典。

    无返回值。
    """
    key = os.getenv('ROBOT_KEY_' + env.upper())
    # 获取external url
    global EXTERNAL_URL
    if not EXTERNAL_URL:
        EXTERNAL_URL = data['externalURL']

    if not key:
        current_app.logger.error(ERROR_KEY_NOT_SET)
        return

    # 构造钉钉消息的URL
    timestamp = int(round(time.time() * 1000))
    url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=%s' % (key)

    # 提取状态信息和报警列表
    status = data.get('status')
    alerts = data.get('alerts', [])
    alert_dict = {}

    # 遍历每个报警，组织按报警名分组
    for alert in alerts:
        try:
            alert_name = alert['labels'].get('alertname')
        except KeyError as e:
            current_app.logger.error("Warning: Alert missing 'labels' or 'labels' missing 'alertname'. Skipping alert.")
            continue

        if alert_name is not None:
            alert_dict.setdefault(alert_name, []).append(alert)

    # 为每组报警生成markdown格式的消息
    for alert_name, alerts_group in alert_dict.items():
        alert_number = len(alerts_group)
        title_firing = '**[%s]** 有 **%d** 条新的报警' % (alert_name, alert_number)
        title_resolved = '**[%s]** 有 **%d** 条报警已经恢复' % (alert_name, alert_number)
        # 为告警生成banner图
        warning_banner_url = f"https://teamo-md.oss-cn-shanghai.aliyuncs.com/alert/warn-r.png"
        resolved_banner_url = f"https://teamo-md.oss-cn-shanghai.aliyuncs.com/alert/resolved-r.png"
        # 生成报警列表的markdown文本，只包含前5条
        alert_list = ''.join(_mark_item(alert) for alert in alerts_group[:5])

        # 组装完整的markdown消息
        if status == 'firing':
            markdown_text = f"{title_firing}\n{alert_list}\n[点击查看完整信息]({EXTERNAL_URL})"
            send_data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": markdown_text
                }
            }
        else:
            markdown_text = f"{title_resolved}\n{alert_list}\n[点击查看完整信息]({EXTERNAL_URL})"
            send_data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": markdown_text
                }
            }

        # 发送消息到钉钉
        req = requests.post(url, json=send_data)
        result = req.json()
        current_app.logger.debug(result)
        # 检查发送结果
        if result['errcode'] != 0:
            current_app.logger.error('notify wechat error: %s' % result['errcode'])


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

        # 确保 'summary' 和 'description' 是非空字符串类型
        summary = str(annotations_data.get('summary', '')).strip()
        description = str(annotations_data.get('description', '')).strip()

        if not isinstance(summary, str) or not isinstance(description, str) or not summary or not description:
            raise ValueError("summary和description必须是非空字符串类型")
    except KeyError as e:
        current_app.logger.error(f"缺少必要的键: {e}", exc_info=True)
        return "处理报警信息时发生错误"
    except ValueError as e:
        current_app.logger.error(f"数据类型错误: {e}", exc_info=True)
        return "处理报警信息时发生错误"

    annotations = f"> 摘要: {summary}\n\n> 描述: {description}\n---\n"
    mark_item = ''

    # 使用字典映射来优化性能和可读性
    label_format_map = {
        'job': "\n> Job: {value}\n\n",
        'namespace': "\n> Namespace: {value}\n\n",
        'pod': "\n> Pod: {value}\n\n",
        'service': "\n> Service: {value}\n\n",
        'status': "\n> Status: {value}\n\n"
    }

    for key, value in labels.items():
        format_string = label_format_map.get(key)
        if format_string:
            mark_item += format_string.format(value=value)

    mark_item += annotations

    return mark_item


def check_token(env):
    try:
        # 通过os.getenv获取环境变量，考虑到敏感信息访问的安全性，此处保持不变
        key = os.getenv('ROBOT_KEY_' + env.upper())

        if key is None:
            # 当环境变量未设置时，使用400状态码反映Bad Request的情况
            return f'Welcome to use Prometheus Alert manager WeChat webhook server! This URL is for {env.upper()} environment. But env not set!', 400
        else:
            # 环境变量设置正确，返回成功信息
            return f'Welcome to use Prometheus Alert manager WeChat webhook server! This URL is for {env.upper()} environment.', 200
    except ValueError as ve:
        # 对于输入验证引发的异常，返回400状态码
        current_app.logger.error(f"Input validation error: {ve}")
        return f'Invalid input: {ve}', 400
    except Exception as e:
        # 对于预期内的其他异常，记录详细错误日志，并返回500状态码
        current_app.logger.error(f"An error occurred: {e}")
        return f'Welcome to use Prometheus Alert manager Dingtalk webhook server! We found an error for {env.upper()} environment: {e}', 500
