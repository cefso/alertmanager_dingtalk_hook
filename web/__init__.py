import logging
import os

from flask import Flask
from flask_siwadoc import SiwaDoc

from web.base_config import config

siwa = SiwaDoc(title="alertmanager hook", description="alertmanager hook 的 api 文档")

# 设置日志记录级别
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')


# db = SQLAlchemy()
# migrate = Migrate()
# siwa = SiwaDoc(title="ex_cms", description="ex cms 的 api 文档")


# 创建flask app
def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # siwa
    siwa.init_app(app)

    # 引入配置文件
    env = os.getenv('FLASK_ENV', 'default')
    app.config.from_object(config[env])
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the health config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # 数据库相关初始化
    # db.init_app(app)
    # migrate.init_app(app, db)

    # 创建表
    # with app.app_context():
    #     db.create_all()

    # from . import alert, health, outgoing, user, cms
    # alert.init_app(app)
    # health.init_app(app)
    # outgoing.init_app(app)
    # user.init_app(app)
    # cms.init_app(app)
    from . import dingtalk, wechat
    dingtalk.init_app(app)
    wechat.init_app(app)

    return app
