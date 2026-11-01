# zfh: 导入 Django 测试基类 TestCase
from django.test import TestCase

# zfh: 导入项目工具模块中的全部工具函数与类
from djangoblog.utils import *


# zfh: djangoblog 应用的测试用例类
class DjangoBlogTest(TestCase):
    # zfh: 测试前置钩子
    def setUp(self):
        # zfh: 空实现，不做额外初始化
        pass

    # zfh: 测试 utils 模块的哈希、Markdown 渲染和字典转 URL 工具
    def test_utils(self):
        # zfh: 计算字符串 'test' 的 sha256 摘要
        md5 = get_sha256('test')
        # zfh: 断言摘要结果不为空
        self.assertIsNotNone(md5)
        # zfh: 将包含标题、代码块和链接的 Markdown 文本渲染为 HTML
        c = CommonMarkdown.get_markdown('''
        # Title1

        ```python
        import os
        ```

        [url](https://www.lylinux.net/)

        [ddd](http://www.baidu.com)


        ''')
        # zfh: 断言渲染结果不为空
        self.assertIsNotNone(c)
        # zfh: 待转换的字典
        d = {
            'd': 'key1',
            'd2': 'key2'
        }
        # zfh: 把字典转换为 URL 查询参数字符串
        data = parse_dict_to_url(d)
        # zfh: 断言转换结果不为空
        self.assertIsNotNone(data)
