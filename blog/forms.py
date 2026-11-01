# ZFH: 表单模块：定义博客搜索表单
import logging

from django import forms
from haystack.forms import SearchForm

logger = logging.getLogger(__name__)


class BlogSearchForm(SearchForm):
    # ZFH: 基于 Haystack SearchForm 扩展的搜索表单，增加必填的 querydata 字段
    querydata = forms.CharField(required=True)  # ZFH: 用户输入的搜索关键词，必填

    def search(self):
        # ZFH: 执行搜索：先调用父类搜索，再校验表单并记录日志，返回结果集
        datas = super(BlogSearchForm, self).search()
        if not self.is_valid():
            return self.no_query_found()

        if self.cleaned_data['querydata']:
            logger.info(self.cleaned_data['querydata'])
        return datas
