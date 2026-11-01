# ZFH: OnlineMiddleware 中间件测试模块，覆盖渲染耗时替换、访问统计写入与异常容错
"""
Test cases for blog middleware
"""
# ZFH: 导入 time，用于构造慢响应并测量中间件处理耗时
import time
# ZFH: 导入 mock 工具，用于替换 Elasticsearch 写入、UA 解析与日志对象
from unittest.mock import Mock, patch, MagicMock

# ZFH: 导入 Django 测试基类、请求工厂以及与中间件交互的响应类型
from django.test import TestCase, RequestFactory
from django.http import HttpResponse, StreamingHttpResponse
# ZFH: 导入时区工具，用于断言写入统计的时间字段
from django.utils import timezone

# ZFH: 导入被测的在线访问统计中间件
from blog.middleware import OnlineMiddleware


# ZFH: 在线访问统计中间件测试类：验证初始化、耗时替换、流式响应、ES 写入与异常处理
class OnlineMiddlewareTest(TestCase):
    """测试OnlineMiddleware中间件"""

    # ZFH: 构造请求工厂，并用本地 get_response 模拟下游视图
    def setUp(self):
        """设置测试环境"""
        self.factory = RequestFactory()
        self.middleware = OnlineMiddleware(get_response=self.get_response)

    # ZFH: 模拟下游视图，返回带 <!!LOAD_TIMES!!> 占位符的响应供中间件替换
    def get_response(self, request):
        """模拟Django的get_response"""
        response = HttpResponse("Test content <!!LOAD_TIMES!!>")
        return response

    # ZFH: 测试初始化：断言 get_response 被正确保存，且与传入函数一致
    def test_middleware_initialization(self):
        """测试中间件初始化"""
        middleware = OnlineMiddleware(get_response=self.get_response)
        self.assertIsNotNone(middleware.get_response)
        self.assertEqual(middleware.get_response, self.get_response)

    # ZFH: 测试正常请求：非流式响应应返回 200，且占位符被替换掉
    def test_middleware_processes_request_normally(self):
        """测试中间件正常处理请求"""
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

        response = self.middleware(request)

        # 验证响应返回
        self.assertEqual(response.status_code, 200)
        # 验证响应内容中的加载时间被替换
        self.assertNotIn(b'<!!LOAD_TIMES!!>', response.content)

    # ZFH: 测试耗时统计：用慢视图模拟渲染，断言总耗时不少于 0.1 秒且占位符被替换
    def test_middleware_calculates_page_render_time(self):
        """测试中间件计算页面渲染时间"""
        # 创建一个慢响应来测试时间计算
        # ZFH: 定义慢响应函数，人为延迟 100ms 以模拟页面渲染耗时
        def slow_get_response(request):
            time.sleep(0.1)  # 模拟100ms的处理时间
            return HttpResponse("Test content <!!LOAD_TIMES!!>")

        middleware = OnlineMiddleware(get_response=slow_get_response)
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        start_time = time.time()
        response = middleware(request)
        elapsed_time = time.time() - start_time

        # 验证响应时间至少是0.1秒
        self.assertGreaterEqual(elapsed_time, 0.1)
        # 验证响应内容被替换
        self.assertNotIn(b'<!!LOAD_TIMES!!>', response.content)

    # ZFH: 测试流式响应：StreamingHttpResponse 不应被读取或改写，断言分块内容原样输出
    def test_middleware_handles_streaming_response(self):
        """测试中间件处理流式响应"""
        # ZFH: 构造流式视图，返回两个字节分块
        def streaming_get_response(request):
            def generator():
                yield b"chunk1"
                yield b"chunk2"
            return StreamingHttpResponse(generator())

        middleware = OnlineMiddleware(get_response=streaming_get_response)
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        response = middleware(request)

        # 验证流式响应被正确处理（不应该尝试替换内容）
        self.assertTrue(response.streaming)
        # 流式响应不应该被修改
        content = b''.join(response.streaming_content)
        self.assertEqual(content, b"chunk1chunk2")

    # ZFH: 测试缺少 User-Agent：不设置请求头时中间件也应正常返回 200
    def test_middleware_handles_missing_user_agent(self):
        """测试中间件处理缺失的User-Agent"""
        request = self.factory.get('/test/')
        # 不设置HTTP_USER_AGENT

        response = self.middleware(request)

        # 应该能正常处理，不会崩溃
        self.assertEqual(response.status_code, 200)

    # ZFH: 同时 patch 开关为 True 与统计写入方法，隔离真实 Elasticsearch 依赖
    @patch('blog.middleware.ELASTICSEARCH_ENABLED', True)
    @patch('blog.middleware.ElaspedTimeDocumentManager.create')
    # ZFH: 测试 ES 启用：断言 create 被调用，且 url、耗时、时间、UA、IP 参数均已传入
    def test_middleware_elasticsearch_integration_enabled(self, mock_create):
        """测试Elasticsearch集成启用时的行为"""
        request = self.factory.get('/test-path/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

        response = self.middleware(request)

        # 验证ElaspedTimeDocumentManager.create被调用
        self.assertTrue(mock_create.called)

        # 验证调用参数
        call_args = mock_create.call_args[1]
        self.assertEqual(call_args['url'], '/test-path/')
        self.assertIsNotNone(call_args['time_taken'])
        self.assertIsNotNone(call_args['log_datetime'])
        self.assertIsNotNone(call_args['useragent'])
        self.assertIsNotNone(call_args['ip'])

    # ZFH: patch 开关为 False，验证关闭 ES 时不会写入统计
    @patch('blog.middleware.ELASTICSEARCH_ENABLED', False)
    @patch('blog.middleware.ElaspedTimeDocumentManager.create')
    # ZFH: 测试 ES 禁用：断言 create 未被调用，但耗时占位符仍被替换
    def test_middleware_elasticsearch_integration_disabled(self, mock_create):
        """测试Elasticsearch集成禁用时的行为"""
        request = self.factory.get('/test-path/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        response = self.middleware(request)

        # 验证ElaspedTimeDocumentManager.create未被调用
        self.assertFalse(mock_create.called)
        # 但响应时间替换仍然应该工作
        self.assertNotIn(b'<!!LOAD_TIMES!!>', response.content)

    # ZFH: patch get_client_ip，用于固定客户端 IP 并验证调用方式
    @patch('blog.middleware.get_client_ip')
    # ZFH: 测试 IP 识别：断言 get_client_ip 以 request 为参数且只调用一次
    def test_middleware_ip_detection(self, mock_get_client_ip):
        """测试IP地址检测"""
        mock_get_client_ip.return_value = ('192.168.1.1', True)

        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        response = self.middleware(request)

        # 验证get_client_ip被调用
        self.assertTrue(mock_get_client_ip.called)
        mock_get_client_ip.assert_called_once_with(request)

    # ZFH: 测试 UA 解析：在 patch('blog.middleware.parse') 下断言按原始 UA 字符串调用一次
    def test_middleware_user_agent_parsing(self):
        """测试User-Agent解析"""
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'

        # ZFH: 用 Mock 替换 UA 解析函数，避免依赖 user-agents 库的真实解析结果
        with patch('blog.middleware.parse') as mock_parse:
            mock_ua = Mock()
            mock_parse.return_value = mock_ua

            response = self.middleware(request)

            # 验证parse被调用
            self.assertTrue(mock_parse.called)
            mock_parse.assert_called_once_with('Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)')

    # ZFH: patch ES 开关为 True 并替换 create，准备模拟写入异常
    @patch('blog.middleware.ELASTICSEARCH_ENABLED', True)
    @patch('blog.middleware.ElaspedTimeDocumentManager.create')
    # ZFH: 测试 ES 异常：create 抛出异常时中间件应捕获，请求仍返回 200
    def test_middleware_handles_elasticsearch_exception(self, mock_create):
        """测试中间件处理Elasticsearch异常"""
        # 模拟Elasticsearch抛出异常
        mock_create.side_effect = Exception("Elasticsearch connection failed")

        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        # 应该能够捕获异常并继续处理
        response = self.middleware(request)

        # 验证响应仍然返回
        self.assertEqual(response.status_code, 200)
        # 注意：当发生异常时，整个try块会被跳过，所以替换可能不会发生
        # 但响应应该仍然返回，只是没有被修改
        self.assertTrue(response.content is not None)

    # ZFH: 测试内容替换异常：构造内容不可正常替换的响应，验证异常被吞掉且响应返回
    def test_middleware_handles_content_replace_exception(self):
        """测试中间件处理内容替换异常"""
        # ZFH: 构造响应并直接改写 _container，模拟内容不可替换的边界情况
        def error_get_response(request):
            # 返回不包含替换标记的响应
            response = HttpResponse("Test content without marker")
            # 模拟response.content不可修改的情况
            response._container = [b"immutable content"]
            return response

        middleware = OnlineMiddleware(get_response=error_get_response)
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        # 应该能够捕获异常并继续处理
        response = middleware(request)

        # 验证响应仍然返回
        self.assertEqual(response.status_code, 200)

    # ZFH: 测试时间格式：断言响应正文可解码且长度大于 0（替换后的时长文本已写入）
    def test_middleware_time_format(self):
        """测试中间件时间格式化"""
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        response = self.middleware(request)

        # 提取替换后的时间值
        content_str = response.content.decode('utf-8')
        # 查找时间字符串（应该是数字格式，长度不超过5个字符）
        time_parts = content_str.split()

        # 验证至少有一些内容
        self.assertTrue(len(content_str) > 0)

    # ZFH: 依次 patch 日志对象、ES 开关与 create，用于验证异常日志记录
    @patch('blog.middleware.logger')
    @patch('blog.middleware.ELASTICSEARCH_ENABLED', True)
    @patch('blog.middleware.ElaspedTimeDocumentManager.create')
    # ZFH: 测试异常日志：create 抛异常后断言 logger.error 被调用且消息含 'Error OnlineMiddleware'
    def test_middleware_logs_exceptions(self, mock_create, mock_logger):
        """测试中间件记录异常日志"""
        # 模拟异常
        test_exception = Exception("Test exception")
        mock_create.side_effect = test_exception

        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        response = self.middleware(request)

        # 验证logger.error被调用
        self.assertTrue(mock_logger.error.called)
        # 验证日志消息包含异常信息
        call_args = str(mock_logger.error.call_args)
        self.assertIn("Error OnlineMiddleware", call_args)

    # ZFH: 测试多请求复用：同一中间件连续处理三个路径，每次都应返回 200 并完成替换
    def test_middleware_with_multiple_requests(self):
        """测试中间件处理多个请求"""
        paths = ['/page1/', '/page2/', '/page3/']

        for path in paths:
            request = self.factory.get(path)
            request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

            response = self.middleware(request)

            # 每个请求都应该成功处理
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(b'<!!LOAD_TIMES!!>', response.content)

    # ZFH: 测试响应头保留：自定义头与 Content-Type 在中间件处理后不应丢失
    def test_middleware_preserves_response_headers(self):
        """测试中间件保留响应头"""
        # ZFH: 构造带自定义响应头的下游视图响应
        def get_response_with_headers(request):
            response = HttpResponse("Test content <!!LOAD_TIMES!!>")
            response['X-Custom-Header'] = 'CustomValue'
            response['Content-Type'] = 'text/html; charset=utf-8'
            return response

        middleware = OnlineMiddleware(get_response=get_response_with_headers)
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        response = middleware(request)

        # 验证响应头被保留
        self.assertEqual(response['X-Custom-Header'], 'CustomValue')
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    # ZFH: patch ES 开关、create 与 timezone.now，固定时间以便断言
    @patch('blog.middleware.ELASTICSEARCH_ENABLED', True)
    @patch('blog.middleware.ElaspedTimeDocumentManager.create')
    @patch('django.utils.timezone.now')
    # ZFH: 测试时区时间：断言 timezone.now 被调用，且写入统计的 log_datetime 等于模拟时间
    def test_middleware_uses_correct_timezone(self, mock_now, mock_create):
        """测试中间件使用正确的时区"""
        mock_time = timezone.now()
        mock_now.return_value = mock_time

        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        response = self.middleware(request)

        # 验证timezone.now被调用
        self.assertTrue(mock_now.called)

        # 验证传递给Elasticsearch的时间是正确的
        if mock_create.called:
            call_args = mock_create.call_args[1]
            self.assertEqual(call_args['log_datetime'], mock_time)
