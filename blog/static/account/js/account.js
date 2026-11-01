// ZFH: 账号相关脚本：忘记密码页的邮箱验证码倒计时与发送 AJAX 逻辑
let wait = 60;

// ZFH: 验证码倒计时函数：每秒递减，归零后恢复按钮可点击状态
function time(o) {
    if (wait == 0) {
        // ZFH: 倒计时结束：移除禁用、恢复按钮文案、重置等待秒数并停止递归
        o.removeAttribute("disabled");
        o.value = "获取验证码";
        wait = 60
        return false
    } else {
        // ZFH: 倒计时进行中：禁用按钮并更新剩余秒数文案
        o.setAttribute("disabled", true);
        o.value = "重新发送(" + wait + ")";
        wait--;
        // ZFH: 1 秒后递归调用自身，形成逐秒递减效果
        setTimeout(function () {
                time(o)
            },
            1000)
    }
}

// ZFH: 给“获取验证码”按钮绑定点击事件，发送邮箱验证码请求
document.getElementById("btn").onclick = function () {
    // ZFH: 读取邮箱输入框、CSRF token 与错误提示 DOM，供 AJAX 请求使用
    let id_email = $("#id_email")
    let token = $("*[name='csrfmiddlewaretoken']").val()
    let ts = this
    let myErr = $("#myErr")
    // ZFH: 以 POST 请求向忘记密码接口提交邮箱与 CSRF token
    $.ajax(
        {
            url: "/forget_password_code/",
            type: "POST",
            data: {
                "email": id_email.val(),
                "csrfmiddlewaretoken": token
            },
            success: function (result) {
                // ZFH: 接口返回非 "ok" 时，把错误信息渲染成错误列表
                if (result != "ok") {
                    myErr.remove()
                    id_email.after("<ul className='errorlist' id='myErr'><li>" + result + "</li></ul>")
                    return
                }
                // ZFH: 发送成功：清除旧错误提示并启动验证码倒计时
                myErr.remove()
                time(ts)
            },
            error: function (e) {
                // ZFH: 请求失败时弹出提示
                alert("发送失败,请重试")
            }
        }
    );
}
