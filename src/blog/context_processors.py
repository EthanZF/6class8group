# ZFH: 上下文处理器：向所有模板注入站点级配置与导航数据
import logging

# ZFH: 引入时区工具，用于实时计算当前年份
from django.utils import timezone

# ZFH: 引入缓存与站点配置读取工具，以及导航所需的分类和文章模型
from djangoblog.utils import cache, get_blog_setting
from .models import Category, Article

# ZFH: 模块级日志记录器，记录缓存未命中等运行信息
logger = logging.getLogger(__name__)


def seo_processor(requests):
    # ZFH: 模板上下文处理器，返回站点名称、SEO、备案、导航分类/页面等全局变量；结果带10小时缓存
    key = 'seo_processor'
    value = cache.get(key)
    if value:
        # ZFH: 更新动态值（不需要缓存的内容：当前域名与年份每次请求实时计算）
        value['SITE_BASE_URL'] = requests.scheme + '://' + requests.get_host() + '/'
        value['CURRENT_YEAR'] = timezone.now().year
        return value
    else:
        logger.info('set processor cache.')
        setting = get_blog_setting()

        # ZFH: 优化查询：预加载关联数据
        nav_category_list = Category.objects.all()
        nav_pages = Article.objects.filter(
            type='p',
            status='p'
        )

        # ZFH: 组装缓存字典，键名即模板中可直接使用的上下文变量
        value = {
            'SITE_NAME': setting.site_name,
            'SHOW_GOOGLE_ADSENSE': setting.show_google_adsense,
            'GOOGLE_ADSENSE_CODES': setting.google_adsense_codes,
            'SITE_SEO_DESCRIPTION': setting.site_seo_description,
            'SITE_DESCRIPTION': setting.site_description,
            'SITE_KEYWORDS': setting.site_keywords,
            'SITE_BASE_URL': requests.scheme + '://' + requests.get_host() + '/',
            'ARTICLE_SUB_LENGTH': setting.article_sub_length,
            'nav_category_list': nav_category_list,  # ZFH: 保持QuerySet
            'nav_pages': nav_pages,  # ZFH: 保持QuerySet
            'OPEN_SITE_COMMENT': setting.open_site_comment,
            'BEIAN_CODE': setting.beian_code,
            'ANALYTICS_CODE': setting.analytics_code,
            "BEIAN_CODE_GONGAN": setting.gongan_beiancode,
            "SHOW_GONGAN_CODE": setting.show_gongan_code,
            "CURRENT_YEAR": timezone.now().year,
            "GLOBAL_HEADER": setting.global_header,
            "GLOBAL_FOOTER": setting.global_footer,
            "COMMENT_NEED_REVIEW": setting.comment_need_review,
            "COLOR_SCHEME": setting.color_scheme,
        }
        # ZFH: 缓存 10 小时（60*60*10 秒），减少每请求的数据库查询
        cache.set(key, value, 60 * 60 * 10)
        return value
