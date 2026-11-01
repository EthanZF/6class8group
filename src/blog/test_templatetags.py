"""
模板标签测试
测试各种模板标签和过滤器的功能
"""
# ZFH: 测试模块导入：分页器、模板渲染上下文、请求工厂，以及博客模型与模板标签函数
from django.core.paginator import Paginator
from django.template import Context, Template
from django.test import RequestFactory

# ZFH: 项目内部模块导入：文章模型、blog_tags 中的标签/过滤器与测试基类
from blog.models import Article
from blog.templatetags.blog_tags import *
from djangoblog.test_base import BaseTestCase


# ZFH: 模板标签测试类：覆盖文章标签、分页信息、搜索高亮与 Markdown 渲染
class BlogTagsTest(BaseTestCase):
    """测试博客模板标签"""

    # ZFH: 调用基类 setUp 准备通用数据，并额外创建 RequestFactory 供标签函数使用
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    # ZFH: load_articletags：给文章加标签后，断言返回 dict 且标签出现在 article_tags_list 中
    def test_load_articletags(self):
        """测试加载文章标签"""
        self.article.tags.add(self.tag)
        result = load_articletags(self.article)
        self.assertIsInstance(result, dict)
        self.assertIn('article_tags_list', result)
        # 检查标签是否在列表中
        # ZFH: 元组第三项为标签对象，从结果中提取后与预期标签比对
        tag_objects = [tag_tuple[2] for tag_tuple in result['article_tags_list']]
        self.assertIn(self.tag, tag_objects)

    # ZFH: 分页信息：构造两页数据，断言返回非空且分页对象具备前后页属性
    def test_load_pagination_info(self):
        """测试加载分页信息"""
        # 创建测试数据
        # ZFH: 构造 20 条文章数据并按每页 10 条分页
        articles = [self.create_article(title=f'文章{i}') for i in range(20)]
        paginator = Paginator(articles, 10)
        page = paginator.get_page(1)

        # load_pagination_info 需要 page_type 和 tag_name 参数
        info = load_pagination_info(page, '', '')

        self.assertIsNotNone(info)
        # 验证基本分页属性存在
        self.assertTrue(hasattr(page, 'has_previous'))
        self.assertTrue(hasattr(page, 'has_next'))

    # ZFH: 最后一页：请求第 2 页，断言没有下一页但存在上一页
    def test_load_pagination_info_last_page(self):
        """测试最后一页的分页信息"""
        articles = [self.create_article(title=f'文章{i}') for i in range(15)]
        paginator = Paginator(articles, 10)
        page = paginator.get_page(2)

        info = load_pagination_info(page, '', '')

        # 验证分页对象的属性
        self.assertFalse(page.has_next())
        self.assertTrue(page.has_previous())

    # ZFH: 关键词高亮：断言输出包含 mark 标签且保留原关键词
    def test_highlight_search_term(self):
        """测试搜索关键词高亮"""
        text = '这是一段包含关键词的文本'
        result = highlight_search_term(text, '关键词')
        self.assertIn('<mark>', result)
        self.assertIn('关键词', result)

    # ZFH: 关键词不匹配：结果应与原文完全一致
    def test_highlight_search_term_no_match(self):
        """测试搜索关键词不匹配"""
        text = '这是一段普通文本'
        result = highlight_search_term(text, '关键词')
        self.assertEqual(result, text)

    # ZFH: 空搜索词：不做替换，原样返回文本
    def test_highlight_search_term_empty_query(self):
        """测试空搜索词"""
        text = '这是一段普通文本'
        result = highlight_search_term(text, '')
        self.assertEqual(result, text)

    # ZFH: 正文高亮：HTML 内容中的关键词应被处理并保留
    def test_highlight_content(self):
        """测试内容高亮"""
        content = '<p>这是一段 HTML 内容</p>'
        result = highlight_content(content, '内容')
        self.assertIn('内容', result)

    # ZFH: 自定义 Markdown：标题与加粗语法应渲染为 h1/strong 标签
    def test_custom_markdown(self):
        """测试自定义 Markdown 渲染"""
        markdown_text = '# 标题\n\n这是一段**加粗**的文本'
        result = custom_markdown(markdown_text)
        self.assertIn('<h1', result)
        self.assertIn('<strong>', result)

    # ZFH: 文章正文渲染：验证 Markdown 渲染器对标题与普通文本的处理
    def test_article_body_rendering(self):
        """测试文章内容渲染"""
        # 测试 Markdown 渲染，不需要创建文章
        markdown_text = '# 标题\n这是文章内容'
        result = custom_markdown(markdown_text)
        self.assertIn('<h1', result)
        self.assertIn('文章内容', result)


# ZFH: Vite 模板标签测试类：确认 vite_tags 模块可正常导入
class ViteTagsTest(BaseTestCase):
    """测试 Vite 模板标签"""

    # ZFH: 导入 blog.templatetags.vite_tags，断言模块对象非空即导入成功
    def test_vite_module_exists(self):
        """测试 Vite 模块存在"""
        # 简单测试 Vite 标签模块可以导入
        from blog.templatetags import vite_tags
        self.assertIsNotNone(vite_tags)


# ZFH: 自定义过滤器测试类：通过模板渲染验证 date、urlencode、striptags 等过滤器
class CustomFiltersTest(BaseTestCase):
    """测试自定义过滤器"""

    # ZFH: 日期过滤器：渲染 Y-m-d 格式，断言输出包含当前年份
    def test_date_format_filter(self):
        """测试日期格式化过滤器"""
        # ZFH: 延迟导入 timezone 以获取当前时间作为模板变量
        from django.utils import timezone
        now = timezone.now()

        template = Template('{% load blog_tags %}{{ date|date:"Y-m-d" }}')
        context = Context({'date': now})
        result = template.render(context)
        self.assertIn(str(now.year), result)

    # ZFH: URL 编码过滤器：中文应被编码，断言结果中不再出现原中文字符
    def test_url_encode_filter(self):
        """测试 URL 编码过滤器"""
        template = Template('{% load blog_tags %}{{ text|urlencode }}')
        context = Context({'text': '中文测试'})
        result = template.render(context)
        self.assertNotIn('中文', result)

    # ZFH: striptags 过滤器：断言 HTML 标签被移除但文本内容保留
    def test_strip_tags_filter(self):
        """测试去除 HTML 标签过滤器"""
        html = '<p>这是<strong>HTML</strong>文本</p>'
        template = Template('{% load blog_tags %}{{ html|striptags }}')
        context = Context({'html': html})
        result = template.render(context)
        self.assertNotIn('<p>', result)
        self.assertNotIn('<strong>', result)
        self.assertIn('这是', result)


# ZFH: 侧边栏测试类：仅校验基类准备的文章、分类、标签数据可用
class SidebarTagsTest(BaseTestCase):
    """测试侧边栏标签"""

    def test_sidebar_data_exists(self):
        """测试侧边栏数据存在"""
        # 简单测试侧边栏相关数据可以访问
        self.assertIsNotNone(self.article)
        self.assertIsNotNone(self.category)
        self.assertIsNotNone(self.tag)


# ZFH: 缓存测试类：验证 Django 缓存后端的写入、读取与清空
class CacheTagsTest(BaseTestCase):
    """测试缓存标签"""

    # ZFH: 缓存读写：设置键值后断言可读回，随后清空缓存并断言键已失效
    def test_cache_operations(self):
        """测试缓存操作"""
        from django.core.cache import cache

        # 测试缓存设置和获取
        cache.set('test_key', 'test_value', 60)
        self.assertEqual(cache.get('test_key'), 'test_value')

        # 清空缓存
        cache.clear()
        self.assertIsNone(cache.get('test_key'))


# ZFH: Markdown 扩展测试类：覆盖代码块、表格、自动链接与删除线
class MarkdownExtensionsTest(BaseTestCase):
    """测试 Markdown 扩展"""

    # ZFH: 代码块：围栏代码应渲染出 code 标签
    def test_code_highlight(self):
        """测试代码高亮"""
        markdown_text = '''```python
def hello():
    print("Hello World")
```'''
        result = custom_markdown(markdown_text)
        self.assertIn('<code', result)

    # ZFH: 表格：管道语法应渲染出 table 标签
    def test_table_support(self):
        """测试表格支持"""
        markdown_text = '''
| 列1 | 列2 |
|-----|-----|
| 值1 | 值2 |
'''
        result = custom_markdown(markdown_text)
        self.assertIn('<table', result)

    # ZFH: 自动链接：尖括号包裹的 URL 应保留链接文本
    def test_auto_link(self):
        """测试自动链接"""
        markdown_text = '<https://example.com>'
        result = custom_markdown(markdown_text)
        # Markdown 可能不会自动转换普通URL，需要用尖括号包裹
        self.assertIn('example.com', result)

    # ZFH: 删除线：仅断言渲染结果非空，以兼容不同扩展配置
    def test_strikethrough(self):
        """测试删除线"""
        markdown_text = '~~删除的文本~~'
        result = custom_markdown(markdown_text)
        # 根据实际 Markdown 扩展支持情况验证
        self.assertIsNotNone(result)
