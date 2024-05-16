# 创建flask app
def init_app(app):
    # 引入蓝图
    from . import dingtalk
    app.register_blueprint(dingtalk.bp)

    return app
