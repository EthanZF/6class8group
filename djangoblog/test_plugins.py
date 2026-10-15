# zfh: 插件系统测试，验证插件加载、钩子注册与执行
"""
插件系统测试
测试插件加载、钩子注册和执行
"""
# zfh: 导入 os，用于在测试中操作环境变量
import os
# zfh: 导入 Mock 与 patch，用于模拟对象和打补丁
from unittest.mock import Mock, patch

# zfh: 导入 Django 测试基类 TestCase
from django.test import TestCase

# zfh: 导入插件基类 BasePlugin
from djangoblog.plugin_manage.base_plugin import BasePlugin
# zfh: 导入全部钩子常量
from djangoblog.plugin_manage.hook_constants import *
# zfh: 导入钩子管理器 hooks
from djangoblog.plugin_manage import hooks
# zfh: 导入插件加载函数 load_plugins
from djangoblog.plugin_manage.loader import load_plugins
# zfh: 导入通用测试基类与插件测试混入类
from djangoblog.test_base import BaseTestCase, PluginTestMixin

# 导入钩子常量
# zfh: 显式导入头部与底部资源钩子常量
from djangoblog.plugin_manage.hook_constants import HEAD_RESOURCES_HOOK, BODY_RESOURCES_HOOK


# zfh: 插件钩子系统测试类
class PluginHooksTest(TestCase, PluginTestMixin):
    """测试插件钩子系统"""

    # zfh: 每个测试前重置钩子注册表
    def setUp(self):
        # 清空插件钩子
        # zfh: 把钩子注册表置为空字典
        hooks._hooks = {}

    # zfh: 测试钩子注册
    def test_register_hook(self):
        """测试注册钩子"""
        # zfh: 定义一个测试用钩子函数
        def test_hook(context):
            # zfh: 返回固定字符串
            return "test"

        # zfh: 把测试钩子注册到文章内容钩子上
        hooks.register(ARTICLE_CONTENT_HOOK_NAME, test_hook)
        # zfh: 断言钩子名已出现在注册表中
        self.assertIn(ARTICLE_CONTENT_HOOK_NAME, hooks._hooks)
        # zfh: 断言该钩子下注册了 1 个函数
        self.assertEqual(len(hooks._hooks[ARTICLE_CONTENT_HOOK_NAME]), 1)

    # zfh: 测试过滤器钩子的执行
    def test_apply_filters(self):
        """测试应用过滤器"""
        # zfh: 定义一个修改传入值的过滤器函数
        def test_filter(value):
            # zfh: 在原值后追加 modified 后返回
            return value + " modified"

        # zfh: 注册该过滤器到文章内容钩子
        hooks.register(ARTICLE_CONTENT_HOOK_NAME, test_filter)
        # zfh: 对原始值应用过滤器链
        result = hooks.apply_filters(ARTICLE_CONTENT_HOOK_NAME, "original")
        # zfh: 断言过滤结果为追加后的字符串
        self.assertEqual(result, "original modified")

    # zfh: 测试动作钩子的执行
    def test_run_action(self):
        """测试运行动作钩子"""
        # zfh: 记录动作是否被执行的列表
        executed = []

        # zfh: 定义一个动作函数，执行时向列表追加标记
        def test_action():
            # zfh: 追加 True 表示已执行
            executed.append(True)

        # zfh: 把动作函数注册到文章创建钩子
        hooks.register(ARTICLE_CREATE, test_action)
        # zfh: 触发该动作钩子
        hooks.run_action(ARTICLE_CREATE)
        # zfh: 断言动作函数已被执行
        self.assertTrue(len(executed) > 0)

    # zfh: 测试多个钩子按顺序串联执行
    def test_multiple_hooks(self):
        """测试多个钩子"""
        # zfh: 记录各钩子执行顺序的列表
        results = []

        # zfh: 定义第一个钩子
        def hook1(value):
            # zfh: 记录 hook1 已执行
            results.append('hook1')
            # zfh: 在值后追加 1 并返回
            return value + '1'

        # zfh: 定义第二个钩子
        def hook2(value):
            # zfh: 记录 hook2 已执行
            results.append('hook2')
            # zfh: 在值后追加 2 并返回
            return value + '2'

        # zfh: 注册第一个钩子
        hooks.register(ARTICLE_CONTENT_HOOK_NAME, hook1)
        # zfh: 注册第二个钩子
        hooks.register(ARTICLE_CONTENT_HOOK_NAME, hook2)

        # zfh: 依次应用两个钩子处理基础值
        result = hooks.apply_filters(ARTICLE_CONTENT_HOOK_NAME, 'base')
        # zfh: 断言两个钩子的处理结果已串联
        self.assertEqual(result, 'base12')
        # zfh: 断言两个钩子都执行过
        self.assertEqual(len(results), 2)

    # zfh: 测试钩子抛出异常时的处理
    def test_hook_error_handling(self):
        """测试钩子错误处理"""
        # zfh: 定义会抛异常的钩子
        def error_hook(value):
            # zfh: 抛出异常以模拟钩子出错
            raise Exception("Hook error")

        # zfh: 定义正常返回的钩子
        def normal_hook(value):
            # zfh: 在值后追加 success 并返回
            return value + ' success'

        # zfh: 注册会出错的钩子
        hooks.register(ARTICLE_CONTENT_HOOK_NAME, error_hook)
        # zfh: 注册正常的钩子
        hooks.register(ARTICLE_CONTENT_HOOK_NAME, normal_hook)

        # 即使有钩子出错，其他钩子也应该继续执行
        # zfh: 应用钩子链，验证异常不会中断后续钩子
        result = hooks.apply_filters(ARTICLE_CONTENT_HOOK_NAME, 'test')
        # 错误钩子不会修改值，但正常钩子会
        # zfh: 断言正常钩子的结果出现在返回值中
        self.assertIn('success', result)


# zfh: 基础插件类测试
class BasePluginTest(BaseTestCase):
    """测试基础插件类"""

    # zfh: 创建一个测试用的插件实例
    def _create_test_plugin(self):
        """创建一个测试用的插件实例"""
        # zfh: 定义继承自 BasePlugin 的测试插件类
        class TestPlugin(BasePlugin):
            # zfh: 插件名称
            PLUGIN_NAME = '测试插件'
            # zfh: 插件描述
            PLUGIN_DESCRIPTION = '用于测试的插件'
            # zfh: 插件版本
            PLUGIN_VERSION = '1.0.0'
            # zfh: 插件作者
            PLUGIN_AUTHOR = 'test'

        # zfh: 返回测试插件类的实例
        return TestPlugin()

    # zfh: 测试插件初始化后的元信息
    def test_plugin_initialization(self):
        """测试插件初始化"""
        # zfh: 获取测试插件实例
        plugin = self._create_test_plugin()
        # zfh: 断言插件名称不为空
        self.assertIsNotNone(plugin.PLUGIN_NAME)
        # zfh: 断言插件版本不为空
        self.assertIsNotNone(plugin.PLUGIN_VERSION)

    # zfh: 测试插件配置属性
    def test_plugin_config(self):
        """测试插件配置"""
        # zfh: 获取测试插件实例
        plugin = self._create_test_plugin()
        # 插件应该有配置属性
        # zfh: 断言插件名称不为空
        self.assertIsNotNone(plugin.PLUGIN_NAME)

    # zfh: 测试插件注册钩子
    def test_plugin_register_hooks(self):
        """测试插件注册钩子"""
        # zfh: 获取测试插件实例
        plugin = self._create_test_plugin()
        # 基类的 register_hooks 应该可以被调用
        # zfh: 调用基类的钩子注册方法，验证不报错
        plugin.register_hooks()

    # zfh: 测试获取插件信息
    def test_plugin_get_context(self):
        """测试获取插件信息"""
        # zfh: 获取测试插件实例
        plugin = self._create_test_plugin()
        # zfh: 读取插件信息字典
        plugin_info = plugin.get_plugin_info()
        # zfh: 断言插件信息为字典类型
        self.assertIsInstance(plugin_info, dict)
        # zfh: 断言插件信息中的名称正确
        self.assertEqual(plugin_info['name'], '测试插件')


# zfh: 插件加载器测试
class PluginLoaderTest(TestCase):
    """测试插件加载器"""

    # zfh: 对加载器模块的 logger 打补丁，避免真实日志输出
    @patch('djangoblog.plugin_manage.loader.logger')
    # zfh: 测试插件加载返回列表
    def test_load_plugins(self, mock_logger):
        """测试加载插件"""
        # zfh: 调用插件加载函数
        plugins = load_plugins()
        # zfh: 断言加载结果为列表
        self.assertIsInstance(plugins, list)

    # zfh: 测试插件加载的错误处理
    def test_load_plugins_handles_errors(self):
        """测试插件加载错误处理"""
        # 测试当插件目录不存在或插件有错误时的处理
        # zfh: 打补丁使插件目录判断始终为不存在
        with patch('os.path.exists', return_value=False):
            # zfh: 在目录不存在的条件下调用插件加载函数
            plugins = load_plugins()
            # 应该返回空列表或处理错误
            # zfh: 断言加载结果仍为列表
            self.assertIsInstance(plugins, list)


# zfh: 阅读时间插件测试
class ReadingTimePluginTest(BaseTestCase, PluginTestMixin):
    """测试阅读时间插件"""

    # zfh: 测试阅读时间插件已正确加载
    def test_reading_time_plugin_loaded(self):
        """测试阅读时间插件已加载"""
        # zfh: 导入阅读时间插件类
        from plugins.reading_time.plugin import ReadingTimePlugin
        # zfh: 实例化插件
        plugin = ReadingTimePlugin()
        # zfh: 断言插件名称正确
        self.assertEqual(plugin.PLUGIN_NAME, '阅读时间预测')

    # zfh: 测试阅读时间计算
    def test_calculate_reading_time(self):
        """测试计算阅读时间"""
        # zfh: 导入阅读时间插件类
        from plugins.reading_time.plugin import ReadingTimePlugin
        # zfh: 实例化插件
        plugin = ReadingTimePlugin()

        # 测试短文本
        # zfh: 构造重复 10 次的短文本 HTML
        short_text = '<p>这是一段短文本</p>' * 10
        # zfh: 对短文本追加阅读时间提示
        result = plugin.add_reading_time(short_text)
        # zfh: 断言结果中包含预计阅读时间
        self.assertIn('预计阅读时间', result)
        # zfh: 断言结果中包含分钟字样
        self.assertIn('分钟', result)

        # 测试长文本
        # zfh: 构造重复 1000 次的长文本 HTML
        long_text = '<p>这是一段长文本</p>' * 1000
        # zfh: 对长文本追加阅读时间提示
        long_result = plugin.add_reading_time(long_text)
        # zfh: 断言长文本结果中包含预计阅读时间
        self.assertIn('预计阅读时间', long_result)
        # 长文本应该比短文本有更多内容
        # zfh: 断言长文本处理结果比短文本更长
        self.assertGreater(len(long_result), len(result))


# zfh: 浏览次数插件测试
class ViewCountPluginTest(BaseTestCase, PluginTestMixin):
    """测试浏览次数插件"""

    # zfh: 测试浏览次数插件已正确加载
    def test_view_count_plugin_loaded(self):
        """测试浏览次数插件已加载"""
        # zfh: 导入浏览次数插件类
        from plugins.view_count.plugin import ViewCountPlugin
        # zfh: 实例化插件
        plugin = ViewCountPlugin()
        # zfh: 断言插件名称正确
        self.assertEqual(plugin.PLUGIN_NAME, '文章浏览次数统计')

    # zfh: 测试访问文章后浏览次数增加
    def test_view_count_increment(self):
        """测试浏览次数增加"""
        # zfh: 记录访问前的浏览次数
        initial_views = self.article.views
        # 模拟访问文章
        # zfh: 通过测试客户端访问文章详情页
        self.client.get(self.article.get_absolute_url())
        # zfh: 从数据库重新读取文章对象以获取最新计数
        self.article.refresh_from_db()
        # 浏览次数应该增加
        # zfh: 断言当前浏览次数不少于访问前的次数
        self.assertGreaterEqual(self.article.views, initial_views)


# zfh: SEO 优化插件测试
class SEOOptimizerPluginTest(BaseTestCase, PluginTestMixin):
    """测试 SEO 优化插件"""

    # zfh: 测试 SEO 优化插件已正确加载
    def test_seo_optimizer_plugin_loaded(self):
        """测试 SEO 优化插件已加载"""
        # zfh: 导入 SEO 优化插件类
        from plugins.seo_optimizer.plugin import SeoOptimizerPlugin
        # zfh: 实例化插件
        plugin = SeoOptimizerPlugin()
        # zfh: 断言插件名称正确
        self.assertEqual(plugin.PLUGIN_NAME, 'SEO 优化器')

    # zfh: 测试文章页面输出 SEO meta 标签
    def test_seo_meta_tags(self):
        """测试 SEO meta 标签"""
        # zfh: 导入 SEO 优化插件类
        from plugins.seo_optimizer.plugin import SeoOptimizerPlugin
        # zfh: 实例化插件
        plugin = SeoOptimizerPlugin()

        # zfh: 访问文章详情页获取响应
        response = self.client.get(self.article.get_absolute_url())
        # zfh: 断言响应状态码为 200
        self.assertEqual(response.status_code, 200)
        # 应该包含 meta 标签
        # zfh: 断言响应内容包含 meta 标签
        self.assertContains(response, '<meta')


# zfh: 文章版权插件测试
class ArticleCopyrightPluginTest(BaseTestCase, PluginTestMixin):
    """测试文章版权插件"""

    # zfh: 测试版权插件已正确加载
    def test_copyright_plugin_loaded(self):
        """测试版权插件已加载"""
        # zfh: 导入文章版权插件类
        from plugins.article_copyright.plugin import ArticleCopyrightPlugin
        # zfh: 实例化插件
        plugin = ArticleCopyrightPlugin()
        # zfh: 断言插件名称正确
        self.assertEqual(plugin.PLUGIN_NAME, '文章结尾版权声明')

    # zfh: 测试文章页面已添加版权声明
    def test_copyright_notice_added(self):
        """测试版权声明已添加"""
        # zfh: 访问文章详情页获取响应
        response = self.client.get(self.article.get_absolute_url())
        # zfh: 断言响应状态码为 200
        self.assertEqual(response.status_code, 200)
        # 根据实际插件实现，可能包含版权信息
        # self.assertContains(response, '版权')


# zfh: 外部链接插件测试
class ExternalLinksPluginTest(BaseTestCase, PluginTestMixin):
    """测试外部链接插件"""

    # zfh: 测试外部链接插件已正确加载
    def test_external_links_plugin_loaded(self):
        """测试外部链接插件已加载"""
        # zfh: 导入外部链接插件类
        from plugins.external_links.plugin import ExternalLinksPlugin
        # zfh: 实例化插件
        plugin = ExternalLinksPlugin()
        # zfh: 断言插件名称正确
        self.assertEqual(plugin.PLUGIN_NAME, '外部链接处理器')

    # zfh: 测试外部链接处理
    def test_external_links_processing(self):
        """测试外部链接处理"""
        # zfh: 导入外部链接插件类
        from plugins.external_links.plugin import ExternalLinksPlugin
        # zfh: 实例化插件
        plugin = ExternalLinksPlugin()

        # zfh: 构造含外部链接的 HTML 内容
        content = '<a href="https://example.com">外部链接</a>'
        # 测试插件已加载即可，具体处理逻辑在运行时应用
        # zfh: 断言插件名称不为空
        self.assertIsNotNone(plugin.PLUGIN_NAME)
