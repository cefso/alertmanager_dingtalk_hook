# alertmanager-dingtalk-hook 
AlertManager 钉钉报警简单服务示例


## 使用

### 基础使用

默认情况下访问地址为`http://<host>:5000/dingtalk/hook/<env>`，其中`env`小写, helm下默认为`pro`且必须存在

当使用`GET`方法进行请求时，会返回这个环境的检查情况，可以用来识别对应环境的环境变量是否配置成功

当使用`POST`方法进行请求时，会正常转发alertmanager的消息到对应钉钉机器人

### 高级使用

如果需要更多推送环境，可以添加环境变量 `ROBOT_TOKEN_<环境名称>` 和 `ROBOT_SECRET_<环境名称>`，环境名称为大写，则alert manager填写的webhook地址：`http://<host>:5000/dingtalk/hook/<env>`，其中`env`小写

例如：

如果添加了
```shell
ROBOT_TOKEN_PRE=<钉钉机器人TOKEN>
ROBOT_SECRET_PRE=<钉钉机器人安全SECRET>
```
则可以通过url`http://<host>:5000/dingtalk/hook/pre` 推送到上面`token`配置的钉钉机器人


## 运行
### 使用`Docker`运行
```shell
docker run -p 5000:5000 --name dingtalk-hook -e ROBOT_TOKEN_PRO=<钉钉机器人TOKEN> -e ROBOT_SECRET_PRO=<钉钉机器人安全SECRET> -e LOG_LEVEL=debug -e EXTERNAL_URL=<alertmanager地址>  -d registry.cn-hangzhou.aliyuncs.com/cefso/dingtalk-hook:0.1.2
```

alert manager填写的webhook地址：`http://<host>:5000/dingtalk/hook/<env>`，其中`env`小写


环境变量配置：

* ROBOT_TOKEN_PRO：钉钉机器人 TOKEN
* ROBOT_SECRET_PRO：为钉钉机器人的安全设置密钥，机器人安全设置页面，加签一栏下面显示的 SEC 开头的字符串
* EXTERNAL_URL：手动指定跳转后的 alert manager，方便查看所有告警，默认为alertmanager消息中的地址
* LOG_LEVEL：日志级别，设置成 `debug` 可以看到 AlertManager WebHook 发送的数据，方便调试使用，不需调试可以不设置该环境变量
* 如果需要更多推送环境，可以添加环境变量 `ROBOT_TOKEN_<环境名称>` 和 `ROBOT_SECRET_<环境名称>`，环境名称为大写，则alert manager填写的webhook地址：`http://<host>:5000/dingtalk/hook/<env>`，其中`env`小写


### 在`Kubernetes`集群中运行
现在已经支持使用`helm`进行部署了，使用上更加方便：

添加`helm`仓库：

```shell
helm repo add cefso  https://cefso.github.io/helm-chart
```
提取valuse模板，进行编辑（必须，需要自行配置钉钉机器人相关`token`）：

```shell
helm show values cefso/alertmanager-dingtalk-hook > dingtalk-hook-values.yaml
```

安装dingtalk-hook
```shell
helm install dingtalk-hook cefso/alertmanager-dingtalk-hook -f dingtalk-hook-values.yaml -n monitoring
```

## 参考文档
* [钉钉自定义机器人文档](https://open-doc.dingtalk.com/microapp/serverapi2/qf2nxq)
* [AlertManager 的使用](https://www.qikqiak.com/k8s-book/docs/57.AlertManager%E7%9A%84%E4%BD%BF%E7%94%A8.html)

