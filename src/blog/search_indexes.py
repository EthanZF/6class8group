# ZFH: Haystack 搜索索引定义（默认 Whoosh 后端），声明文章如何被索引与检索
# ZFH: 第三方导入：Haystack 索引基类与字段类型
from haystack import indexes

# ZFH: 项目内导入：待建立索引的文章模型
from blog.models import Article


class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
    # ZFH: 文章搜索索引；text 为主文档字段，通过模板渲染决定索引内容
    # ZFH: 字段声明区：text 是全文检索入口，title/body 额外存储以便结果展示
    text = indexes.CharField(document=True, use_template=True)  # ZFH: 主文档字段，内容由模板生成
    title = indexes.CharField(model_attr='title', stored=True)  # ZFH: 标题字段，取模型属性并存储
    body = indexes.CharField(model_attr='body', stored=True)  # ZFH: 正文字段，取模型属性并存储

    def get_model(self):
        # ZFH: 返回该索引关联的模型
        return Article

    def index_queryset(self, using=None):
        # ZFH: 指定参与索引的查询集，仅索引已发布（status='p'）的文章
        return self.get_model().objects.filter(status='p')
