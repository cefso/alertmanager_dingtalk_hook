from web import siwa, create_app

app = create_app()


@app.route('/', methods=['GET'])
@siwa.doc()
def hello():
    """
    首页路由，返回欢迎信息。
    """
    return 'welcome to use prometheus alert manager dingtalk webhook server!'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
