"""blog 应用的表单定义。

【文件作用】
    存放 blog 应用用到的表单（Form）。表单在 Django 里负责两件事：
      1. 校验用户提交的数据是否合法（validation）；
      2. 把校验后的数据渲染成 HTML 表单控件。
    本文件目前只有一个表单：博客的搜索表单。
"""
import logging

from django import forms
# PSJ SearchForm 是 haystack（全文检索框架）自带的搜索表单基类，
# PSJ 里面已经实现了查询、分页等逻辑，我们只需继承（inherit）并补充自己的字段。
from haystack.forms import SearchForm

# PSJ 按模块名创建 logger，便于在日志里定位是哪个文件输出的信息。
logger = logging.getLogger(__name__)


class BlogSearchForm(SearchForm):
    """博客搜索表单。

    为什么继承 haystack 的 SearchForm：
        搜索功能底层用的是 haystack（配合 Whoosh 检索引擎），
        它已经写好了 search() 方法去查索引，这里只需要定义"用户输入的字段"。
    """

    # PSJ 搜索关键词字段（field）。required=True 表示必填，为空时表单校验不通过。
    querydata = forms.CharField(required=True)

    def search(self):
        """执行搜索。

        返回值是搜索结果集（SearchQuerySet），交给视图和模板去渲染。
        """
        # PSJ 先调用父类的 search()，由 haystack 按字段去检索索引（index）并返回结果。
        datas = super(BlogSearchForm, self).search()

        # PSJ 如果表单校验（validation）没通过（例如关键词为空），
        # PSJ 就返回一个"空结果集"，避免把不完整的数据传下去。
        if not self.is_valid():
            return self.no_query_found()

        # PSJ cleaned_data 是 Django 校验通过后的"干净数据"。
        # PSJ 这里只把关键词记进日志（log），方便排查用户都搜了什么。
        if self.cleaned_data['querydata']:
            logger.info(self.cleaned_data['querydata'])

        # PSJ 返回检索结果。
        return datas
