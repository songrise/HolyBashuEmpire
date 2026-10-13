# 巴蜀事件档案

一个只读取模组源码的本地开发工具，不需要启动 EU5，不会写入游戏、存档或创意工坊。仅使用 Python 标准库和原生 HTML / CSS / JavaScript，无需安装前端依赖。

## 启动

在 PowerShell 中运行 `./Start-Event-Browser.ps1`，或右键脚本选择「使用 PowerShell 运行」。默认地址为 http://127.0.0.1:8765，只绑定本机。

默认读取仓库中的 `mod/holy_bashu_empire`；在开发工作区中则读取 `work/v020/mod/holy_bashu_empire`。可指定其他版本：

```powershell
./Start-Event-Browser.ps1 -ModPath 'D:/my-mod/holy_bashu_empire' -Port 8766
```

点击「重新读取源码」即可看到文本或脚本的修改。关闭网页不会结束后台服务，运行 `./Stop-Event-Browser.ps1` 停止本工具启动的进程。

## 浏览

- 搜索事件 ID、标题、正文、选项、国家及效果脚本。
- 按事件系列、七圈、可见 / 隐藏、选项数量筛选。
- 对比每个选项的选择条件、金币 / 威望 / 变量变化、修正数值与期限。
- 展开脚本函数、条件分支、预先执行与完整事件脚本。
- 查看直接调用来源和后续事件；复制 ID 或源码路径。
- 用 ↑ / ↓ 浏览目录，按 / 聚焦搜索框；导出当前完整事件目录为 JSON。

AI 显示的是脚本基础权重，不是实际概率。游戏动态文本以方括号标记；未知效果保留原始标识。条件与作用域保留在嵌套结构中，展开原始脚本可以核对。引用索引只追踪当前模组的直接调用，不模拟引擎运行。地区根据事件脚本、调用位置的 if 条件及国家登记推导。

## 验证及命令行

```powershell
python test_catalog.py
python server.py --mod-path '../../mod/holy_bashu_empire' --export events.json
python server.py --port 8765
```

本目录是开发工具，不应放进创意工坊的 `mod/holy_bashu_empire` 运行包。
