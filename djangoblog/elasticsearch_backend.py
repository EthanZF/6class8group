# zfh: 导入字符串强制转换函数，兼容Python2/3
from django.utils.encoding import force_str
# zfh: 导入Elasticsearch DSL的查询构造类
from elasticsearch_dsl import Q
# zfh: 导入haystack搜索后端基类与查询日志装饰器
from haystack.backends import BaseEngine, BaseSearchBackend, BaseSearchQuery, log_query
# zfh: 导入haystack的模型搜索表单
from haystack.forms import ModelSearchForm
# zfh: 导入haystack搜索结果模型
from haystack.models import SearchResult
# zfh: 导入haystack的日志工具并别名为logging
from haystack.utils import log as logging

# zfh: 导入文章索引文档及其管理器
from blog.documents import ArticleDocument, ArticleDocumentManager
# zfh: 导入文章模型
from blog.models import Article

# zfh: 创建本模块的日志记录器
logger = logging.getLogger(__name__)


# zfh: Elasticsearch搜索后端，基于haystack后端基类实现
class ElasticSearchBackend(BaseSearchBackend):
    # zfh: 初始化后端，完成父类初始化并创建文档管理器
    def __init__(self, connection_alias, **connection_options):
        # zfh: 调用父类初始化方法，传入连接别名与连接参数
        super(
            ElasticSearchBackend,
            self).__init__(
            connection_alias,
            **connection_options)
        # zfh: 创建文章文档管理器实例
        self.manager = ArticleDocumentManager()
        # zfh: 开启拼写建议功能
        self.include_spelling = True

    # zfh: 将传入的可迭代对象转换为文档列表
    def _get_models(self, iterable):
        # zfh: 传入为空时取全部文章，否则使用传入对象
        models = iterable if iterable and iterable[0] else Article.objects.all()
        # zfh: 将模型对象转换为文档
        docs = self.manager.convert_to_doc(models)
        # zfh: 返回转换后的文档列表
        return docs

    # zfh: 创建索引并重建全部文档
    def _create(self, models):
        # zfh: 创建索引
        self.manager.create_index()
        # zfh: 获取待写入的文档
        docs = self._get_models(models)
        # zfh: 重建索引中的文档
        self.manager.rebuild(docs)

    # zfh: 删除给定模型对应的索引文档
    def _delete(self, models):
        # zfh: 遍历并逐个删除文档
        for m in models:
            # zfh: 删除当前文档
            m.delete()
        # zfh: 返回删除成功
        return True

    # zfh: 重建索引文档
    def _rebuild(self, models):
        # zfh: 传入为空时取全部文章，否则使用传入对象
        models = models if models else Article.objects.all()
        # zfh: 将模型对象转换为文档
        docs = self.manager.convert_to_doc(models)
        # zfh: 更新索引中的文档
        self.manager.update_docs(docs)

    # zfh: 更新索引，将可迭代对象写入Elasticsearch
    def update(self, index, iterable, commit=True):

        # zfh: 将传入对象转换为文档
        models = self._get_models(iterable)
        # zfh: 更新索引中的文档
        self.manager.update_docs(models)

    # zfh: 从索引中移除指定对象
    def remove(self, obj_or_string):
        # zfh: 将单个对象包装为列表并转换为文档
        models = self._get_models([obj_or_string])
        # zfh: 删除转换得到的文档
        self._delete(models)

    # zfh: 清空索引
    def clear(self, models=None, commit=True):
        # zfh: 传入None时_get_models会取全部文章，从而清空索引
        self.remove(None)

    # zfh: 声明为静态方法
    @staticmethod
    # zfh: 获取搜索推荐词，未找到时返回原搜索词
    def get_suggestion(query: str) -> str:
        """获取推荐词, 如果没有找到添加原搜索词"""

        # zfh: 构造匹配查询并按body字段生成拼写建议后执行
        search = ArticleDocument.search() \
            .query("match", body=query) \
            .suggest('suggest_search', query, term={'field': 'body'}) \
            .execute()

        # zfh: 存放推荐关键词列表
        keywords = []
        # zfh: 遍历拼写建议结果
        for suggest in search.suggest.suggest_search:
            # zfh: 存在候选词时取第一个候选词文本
            if suggest["options"]:
                # zfh: 追加排序最靠前的候选词
                keywords.append(suggest["options"][0]["text"])
            # zfh: 无候选词时使用原词
            else:
                # zfh: 追加原始搜索词
                keywords.append(suggest["text"])

        # zfh: 用空格拼接关键词并返回
        return ' '.join(keywords)

    # zfh: 装饰器，记录本次查询日志
    @log_query
    # zfh: 执行搜索，返回结果、总数、分面与拼写建议
    def search(self, query_string, **kwargs):
        # zfh: 记录本次搜索的查询串
        logger.info('search query_string:' + query_string)

        # zfh: 取出结果起始偏移
        start_offset = kwargs.get('start_offset')
        # zfh: 取出结果结束偏移
        end_offset = kwargs.get('end_offset')
        # zfh: 取出是否高亮，默认启用高亮
        highlight = kwargs.get('highlight', True)  # 默认启用高亮

        # 推荐词搜索
        # zfh: 后端标记为建议搜索时先获取推荐词
        if getattr(self, "is_suggest", None):
            # zfh: 获取推荐搜索词
            suggestion = self.get_suggestion(query_string)
        # zfh: 否则直接使用原搜索词
        else:
            # zfh: 使用原始查询串
            suggestion = query_string

        # zfh: 构造布尔查询，正文或标题匹配推荐词
        q = Q('bool',
              should=[Q('match', body=suggestion), Q('match', title=suggestion)],
              minimum_should_match=1)  # 至少匹配1个should子句

        # zfh: 构造文章查询，过滤已发布且类型为文章的数据
        search = ArticleDocument.search() \
                     .query('bool', filter=[q]) \
                     .filter('term', status='p') \
                     .filter('term', type='a')

        # 添加高亮配置
        # zfh: 启用高亮时配置标题与正文的高亮参数
        if highlight:
            # zfh: 设置高亮字段、片段大小数量及前后标签
            search = search.highlight('title', 'body',
                                    fragment_size=150,  # 片段大小
                                    number_of_fragments=3,  # 片段数量
                                    pre_tags=['<mark>'],  # 高亮开始标签
                                    post_tags=['</mark>'])  # 高亮结束标签

        # zfh: 不返回原始字段并按偏移切片实现分页
        search = search.source(False)[start_offset: end_offset]

        # zfh: 执行查询得到结果
        results = search.execute()
        # ES 8.x: total 现在是对象 {'value': 123, 'relation': 'eq'}
        # zfh: 取出命中总数，ES 8.x中为对象
        hits_total = results['hits']['total']
        # zfh: 兼容新旧格式，取出命中总数的数值
        hits = hits_total['value'] if isinstance(hits_total, dict) else hits_total
        # zfh: 存放转换后的搜索结果列表
        raw_results = []
        # zfh: 遍历每条命中的原始结果
        for raw_result in results['hits']['hits']:
            # zfh: 结果所属应用标签固定为blog
            app_label = 'blog'
            # zfh: 结果模型名固定为Article
            model_name = 'Article'
            # zfh: 存放构造搜索结果所需的附加字段
            additional_fields = {}

            # 添加高亮内容
            # zfh: 启用高亮且该结果含高亮片段时组装高亮内容
            if highlight and 'highlight' in raw_result:
                # zfh: 存放各字段的高亮片段
                highlighted = {}
                # zfh: 存在标题高亮时写入标题片段
                if 'title' in raw_result['highlight']:
                    # zfh: 取出标题高亮片段
                    highlighted['title'] = raw_result['highlight']['title']
                # zfh: 存在正文高亮时写入正文片段
                if 'body' in raw_result['highlight']:
                    # zfh: 取出正文高亮片段
                    highlighted['body'] = raw_result['highlight']['body']

                # zfh: 有高亮内容时写入附加字段
                if highlighted:
                    # zfh: 将高亮内容挂到附加字段上
                    additional_fields['highlighted'] = highlighted

            # zfh: 指定搜索结果类
            result_class = SearchResult

            # zfh: 用应用标签、模型名、文档id与得分构造搜索结果对象
            result = result_class(
                app_label,
                model_name,
                raw_result['_id'],
                raw_result['_score'],
                **additional_fields)
            # zfh: 将结果对象加入结果列表
            raw_results.append(result)
        # zfh: 分面结果置空
        facets = {}
        # zfh: 推荐词与原查询不同时返回推荐词，否则为None
        spelling_suggestion = None if query_string == suggestion else suggestion

        # zfh: 返回haystack要求的搜索结果字典
        return {
            'results': raw_results,
            'hits': hits,
            'facets': facets,
            'spelling_suggestion': spelling_suggestion,
        }


# zfh: Elasticsearch查询类，基于haystack查询基类
class ElasticSearchQuery(BaseSearchQuery):
    # zfh: 将日期对象转换为Elasticsearch可用的时间字符串
    def _convert_datetime(self, date):
        # zfh: 带小时信息时按精确到秒的格式转换
        if hasattr(date, 'hour'):
            # zfh: 格式化为年月日时分秒
            return force_str(date.strftime('%Y%m%d%H%M%S'))
        # zfh: 不带小时信息时按当天零点格式转换
        else:
            # zfh: 格式化为年月日加六个零
            return force_str(date.strftime('%Y%m%d000000'))

    # zfh: 清洗用户输入的查询片段
    def clean(self, query_fragment):
        """
        Provides a mechanism for sanitizing user input before presenting the
        value to the backend.

        Whoosh 1.X differs here in that you can no longer use a backslash
        to escape reserved characters. Instead, the whole word should be
        quoted.
        """
        # zfh: 按空白拆分查询片段
        words = query_fragment.split()
        # zfh: 存放清洗后的词
        cleaned_words = []

        # zfh: 逐个词进行清洗
        for word in words:
            # zfh: 命中保留字时转为小写
            if word in self.backend.RESERVED_WORDS:
                # zfh: 将保留字替换为小写形式
                word = word.replace(word, word.lower())

            # zfh: 遍历保留字符
            for char in self.backend.RESERVED_CHARACTERS:
                # zfh: 词中含保留字符时整体加单引号
                if char in word:
                    # zfh: 用单引号包裹该词
                    word = "'%s'" % word
                    # zfh: 已处理，跳出字符循环
                    break

            # zfh: 加入清洗结果列表
            cleaned_words.append(word)

        # zfh: 用空格拼接清洗后的词并返回
        return ' '.join(cleaned_words)

    # zfh: 构造查询片段，直接返回查询串
    def build_query_fragment(self, field, filter_type, value):
        # zfh: 返回值的query_string属性
        return value.query_string

    # zfh: 获取结果总数
    def get_count(self):
        # zfh: 获取查询结果
        results = self.get_results()
        # zfh: 有结果时返回长度，否则返回0
        return len(results) if results else 0

    # zfh: 获取拼写建议
    def get_spelling_suggestion(self, preferred_query=None):
        # zfh: 返回后端保存的拼写建议
        return self._spelling_suggestion

    # zfh: 构造查询参数
    def build_params(self, spelling_query=None):
        # zfh: 调用父类方法生成参数
        kwargs = super(ElasticSearchQuery, self).build_params(spelling_query=spelling_query)
        # zfh: 返回参数
        return kwargs


# zfh: Elasticsearch模型搜索表单，基于haystack搜索表单扩展
class ElasticSearchModelSearchForm(ModelSearchForm):

    # zfh: 执行搜索
    def search(self):
        # 是否建议搜索
        # zfh: 根据请求参数设置后端是否启用建议搜索
        self.searchqueryset.query.backend.is_suggest = self.data.get("is_suggest") != "no"
        # zfh: 调用父类执行搜索
        sqs = super().search()
        # zfh: 返回搜索集
        return sqs


# zfh: Elasticsearch搜索引擎，组合后端与查询类
class ElasticSearchEngine(BaseEngine):
    # zfh: 指定使用的搜索后端
    backend = ElasticSearchBackend
    # zfh: 指定使用的查询类
    query = ElasticSearchQuery
