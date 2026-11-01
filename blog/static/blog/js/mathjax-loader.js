// ZFH: 数学公式智能加载器：检测页面是否含 LaTeX 公式，有则动态加载并配置 MathJax，无则跳过
/**
 * MathJax 智能加载器
 * 检测页面是否包含数学公式，如果有则动态加载和配置MathJax
 */
// ZFH: 使用立即执行函数（IIFE）隔离作用域，避免内部变量污染全局
(function() {
    'use strict';
    
    /**
     * 检测页面是否包含数学公式
     * 只扫描文章正文区域，并排除 pre/code 代码块，
     * 避免 $PATH、$(cmd) 等 Shell 变量触发误判
     * @returns {boolean} 是否包含数学公式
     */
    // ZFH: 检测正文是否含数学公式：仅扫描正文容器，排除代码块，用正则匹配 LaTeX 语法
    function hasMathFormulas() {
        // 只检查文章正文，范围外不做处理
        var article = document.querySelector('.article.prose, .entry-content, #content');
        if (!article) return false;

        // 浅复制后移除 pre/code，避免代码片段干扰
        var clone = article.cloneNode(true);
        clone.querySelectorAll('pre, code').forEach(function(el) { el.remove(); });
        var content = clone.textContent || '';

        // 仅匹配明确的 LaTeX 语法：
        //   $$...$$  块级公式
        //   \[...\]  块级公式（另一种写法）
        //   \begin{env} LaTeX 环境
        return /\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\begin\{[a-zA-Z]+\*?\}/.test(content);
    }
    
    /**
     * 配置MathJax
     */
    // ZFH: 配置 MathJax：设置公式分隔符、跳过的标签、启动回调与输出参数
    function configureMathJax() {
        window.MathJax = {
            tex: {
                // 行内公式和块级公式分隔符
                inlineMath: [['$', '$']],
                displayMath: [['$$', '$$']],
                // 处理转义字符和LaTeX环境
                processEscapes: true,
                processEnvironments: true,
                // 自动换行
                tags: 'ams'
            },
            options: {
                // 跳过这些HTML标签，避免处理代码块等
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'a'],
                // CSS类控制
                ignoreHtmlClass: 'tex2jax_ignore',
                processHtmlClass: 'tex2jax_process'
            },
            // 启动配置
            startup: {
                ready() {
                    // ZFH: 初始化完成后，对正文与评论区分别执行公式渲染
                    console.log('MathJax配置完成，开始初始化...');
                    MathJax.startup.defaultReady();
                    
                    // 处理特定区域的数学公式
                    const contentEl = document.getElementById('content');
                    const commentsEl = document.getElementById('comments');
                    
                    const promises = [];
                    if (contentEl) {
                        promises.push(MathJax.typesetPromise([contentEl]));
                    }
                    if (commentsEl) {
                        promises.push(MathJax.typesetPromise([commentsEl]));
                    }
                    
                    // 等待所有渲染完成
                    Promise.all(promises).then(() => {
                        console.log('MathJax渲染完成');
                        // 触发自定义事件，通知其他脚本MathJax已就绪
                        document.dispatchEvent(new CustomEvent('mathjaxReady'));
                    }).catch(error => {
                        console.error('MathJax渲染失败:', error);
                    });
                }
            },
            // 输出配置
            chtml: {
                scale: 1,
                minScale: 0.5,
                matchFontHeight: false,
                displayAlign: 'center',
                displayIndent: '0'
            }
        };
    }
    
    /**
     * 加载MathJax库
     */
    // ZFH: 动态加载 MathJax 脚本，失败时回退到备用 CDN
    function loadMathJax() {
        console.log('检测到数学公式，开始加载MathJax...');
        
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js';
        script.async = true;
        script.defer = true;
        
        script.onload = function() {
            console.log('MathJax库加载成功');
        };
        
        script.onerror = function() {
            console.error('MathJax库加载失败，尝试备用CDN...');
            // 备用CDN
            const fallbackScript = document.createElement('script');
            fallbackScript.src = 'https://polyfill.io/v3/polyfill.min.js?features=es6';
            fallbackScript.onload = function() {
                const mathJaxScript = document.createElement('script');
                mathJaxScript.src = 'https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-MML-AM_CHTML';
                mathJaxScript.async = true;
                document.head.appendChild(mathJaxScript);
            };
            document.head.appendChild(fallbackScript);
        };
        
        document.head.appendChild(script);
    }
    
    /**
     * 初始化函数
     */
    // ZFH: 初始化：等待 DOM 就绪后检测公式，命中才加载 MathJax
    function init() {
        // 等待DOM完全加载
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }
        
        // 检测是否需要加载MathJax
        if (hasMathFormulas()) {
            // 先配置，再加载
            configureMathJax();
            loadMathJax();
        } else {
            console.log('未检测到数学公式，跳过MathJax加载');
        }
    }
    
    // 提供重新渲染的全局方法，供动态内容使用
    // ZFH: 暴露全局重渲染方法，供动态插入内容后手动重新排版公式
    window.rerenderMathJax = function(element) {
        if (window.MathJax && window.MathJax.typesetPromise) {
            const target = element || document.body;
            return window.MathJax.typesetPromise([target]);
        }
        return Promise.resolve();
    };
    
    // 启动初始化
    // ZFH: 立即启动加载器
    init();
})();
