# zfh: 导入日志模块
import logging

# zfh: 导入 requests 库，用于发送 HTTP 请求
import requests
# zfh: 导入 Django 配置，读取 settings 中的全局设置
from django.conf import settings

# zfh: 以当前模块名创建日志记录器
logger = logging.getLogger(__name__)


# zfh: 蜘蛛通知类，向搜索引擎推送新链接
class SpiderNotify():
    # zfh: 静态方法，无需实例即可调用
    @staticmethod
    # zfh: 向百度推送一组 URL
    def baidu_notify(urls):
        # zfh: 尝试执行推送，捕获其中的异常
        try:
            # zfh: 把 URL 列表用换行符拼接成请求体
            data = '\n'.join(urls)
            # zfh: 向百度通知接口发送 POST 请求
            result = requests.post(settings.BAIDU_NOTIFY_URL, data=data)
            # zfh: 记录接口返回的文本
            logger.info(result.text)
        # zfh: 捕获推送过程中的异常
        except Exception as e:
            # zfh: 记录异常信息
            logger.error(e)

    # zfh: 静态方法，无需实例即可调用
    @staticmethod
    # zfh: 推送 URL 到搜索引擎的通知入口
    def notify(url):
        # zfh: 调用百度推送方法完成通知
        SpiderNotify.baidu_notify(url)
