# 创建flask app
def init_app(app):
    # 引入蓝图
    from . import wechat
    app.register_blueprint(wechat.bp)

    return app
