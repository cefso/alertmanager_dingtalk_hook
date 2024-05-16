import os

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:  # 基本配置类
    # SECRET_KEY = os.getenv('SECRET_KEY', 'some secret words')
    FLASK_ENV = os.getenv('FLASK_ENV', 'default')
    ITEMS_PER_PAGE = 10


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # ROBOT_APP_SECRET = os.getenv('ROBOT_APP_SECRET')
    # SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    # SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    # SQLALCHEMY_TRACK_MODIFICATIONS = True
    # SCHEDULER_API_ENABLED = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    # ROBOT_APP_SECRET = os.getenv('ROBOT_APP_SECRET')
    # SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    # SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    # SQLALCHEMY_TRACK_MODIFICATIONS = True
    # SCHEDULER_API_ENABLED = True


config = {
    'default': DevelopmentConfig,
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
