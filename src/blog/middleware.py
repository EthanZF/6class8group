# ZFH: 中间件模块：统计页面渲染耗时并（可选）记录到 Elasticsearch
import logging
import time

# ZFH: 引入第三方 IP 解析与 User-Agent 解析库，用于采集访问来源信息
from ipware import get_client_ip
from user_agents import parse

# ZFH: 引入 ES 开关与耗时文档管理器，用于把性能数据写入索引
from blog.documents import ELASTICSEARCH_ENABLED, ElaspedTimeDocumentManager

# ZFH: 模块级日志记录器，记录统计过程中的异常
logger = logging.getLogger(__name__)


class OnlineMiddleware(object):
    # ZFH: 在线/性能统计中间件，包裹请求-响应流程测量渲染耗时
    def __init__(self, get_response=None):
        # ZFH: Django 新式中间件约定：保存 get_response 回调
        self.get_response = get_response
        # ZFH: 调用父类初始化，兼容旧式中间件基类
        super().__init__()

    def __call__(self, request):
        ''' ZFH: 请求进入时记录起始时间，响应返回后计算耗时 '''
        # ZFH: 记录请求处理前的时间戳，作为耗时统计起点
        start_time = time.time()
        # ZFH: 继续执行后续中间件与视图，拿到最终响应对象
        response = self.get_response(request)
        # ZFH: 读取请求头中的 User-Agent，缺失时用空字符串兜底
        http_user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip, _ = get_client_ip(request)  # ZFH: 从请求中解析客户端IP
        user_agent = parse(http_user_agent)  # ZFH: 解析 UA 字符串
        if not response.streaming:  # ZFH: 流式响应无法替换内容，跳过统计
            # ZFH: 统计逻辑整体包裹 try，任何异常都不影响页面正常返回
            try:
                # ZFH: 计算请求处理耗时（秒）
                cast_time = time.time() - start_time
                if ELASTICSEARCH_ENABLED:
                    # ZFH: 启用 ES 时把耗时记录写入 performance 索引
                    # ZFH: 将秒转换为毫秒并保留两位小数，便于展示与聚合
                    time_taken = round((cast_time) * 1000, 2)
                    # ZFH: 记录请求路径作为性能数据的维度
                    url = request.path
                    from django.utils import timezone
                    # ZFH: 写入 URL、耗时、时间、UA 与 IP 等字段，供后台分析
                    ElaspedTimeDocumentManager.create(
                        url=url,
                        time_taken=time_taken,
                        log_datetime=timezone.now(),
                        useragent=user_agent,
                        ip=ip)
                # ZFH: 将模板中的占位符替换为实际耗时（取前5位字符）
                response.content = response.content.replace(
                    b'<!!LOAD_TIMES!!>', str.encode(str(cast_time)[:5]))
            except Exception as e:
                # ZFH: 统计失败不应影响正常响应，仅记录错误
                logger.error("Error OnlineMiddleware: %s" % e)

        # ZFH: 返回原响应对象；未做替换时内容保持视图输出不变
        return response
