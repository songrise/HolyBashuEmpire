# 可复用开发工具

统一入口：`python tools/dev.py --help`。命令从 `devtools.json` 读取仓库配置，版本从模组 `.metadata/metadata.json` 读取。机器差异放在忽略的 `.devtools.local.json`，可参考根目录示例；`HBE_GAME_DIR` 可覆盖游戏目录。使用与依赖相符的 Python，建议设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONIOENCODING=utf-8`。

这套工具接管重复的运行流程，玩法生成器、原版脚本语义和视觉验收仍保持独立。历史 `work/*vXXX*` 脚本作为证据保留，新任务不要复制它们改日期。特别是旧安装验证脚本可能修改发布记录，后续用只读 `artifact` 命令。

## 模块边界

|模块|职责|
|---|---|
|`devkit/context.py`|仓库、机器配置、元数据版本与环境检查|
|`devkit/artifacts.py`|文件清单、manifest 身份、可选完整 hash、发布计划的修改检测|
|`devkit/profiles.py`|隔离测试目录、播放集、场景与输入快照|
|`devkit/runner.py`、`processes.py`|无窗口运行、超时、进程身份核验、明确停止状态|
|`devkit/telemetry.py`|只在隔离副本中增加地方事业被动计数，不增加随机抽取或资源|
|`devkit/reporting.py`|调用 `eu5save`、检查点统计、逐国数据、受控状态断言、JSON/Markdown 报告|
|`devkit/diagnostics.py`|多行日志归组、登记/脚本/GUI与本地化/资源/其他引擎诊断、基线比较|
|`devkit/workshop.py`、`steam.py`|本地发布计划、显式上传、各语言回读；SDK 仅在发布或回读命令中加载|
|`devkit/registry.py`|复用已有专项验证器和单元测试；不默认全量检查|
|`devkit/pipeline.py`|原构建末尾 42 个阶段的顺序与调用签名；恢复旧美术导出器的全局状态|
|`devkit/media.py`|共享截图嵌入、纸纹文字区、导出和区域外像素保留检查|
|`devkit/archive.py`|选择性归档测试证据，验证 ZIP CRC；不删除来源|

`eu5save` 继续独立负责存档语法与语义，`pdxscript` 继续负责源脚本块编辑，`package_mod.py` 继续负责发行压缩，不产生第二套实现。

## 日常检查

```powershell
python tools/dev.py doctor
python tools/dev.py unit --scope devkit --output work/devkit-unit.json
python tools/dev.py unit --scope parser
python tools/dev.py unit --scope package
python tools/dev.py check --scope hygiene --output work/hygiene.json
python tools/dev.py check --scope local-affairs --output work/affairs.json
```

`hygiene` 复用旧资源描述、重复本地化、Concept 正式名称和变量孤儿检查，不自动删除疑似遗留状态。修改某类规则时扩展已有验证器，再注册范围。

`unit --scope all` 明确运行全部 Python 单元测试，不构建模组。真实存档集成测试仍由 `EU5_SAVE_REFERENCE`、`EU5_SAVE_DIR` 显式启用。

归档观察报告回归使用 `HBE_OBSERVATION_PROFILE` 和 `HBE_OBSERVATION_REFERENCE`，比较每个日期的汇总、同局身份、AI 判定计数和原状态保留。`unit --output` 将结果写成结构化 JSON，包含跳过原因和失败详情。

普通 `artifact <目录>` 检查文件清单及 manifest 身份，不逐文件重算 hash。只有显式添加 `--hashes` 才执行完整内容核对。体积以实际字节数输出，不写死文件数量。

完整构建只由 `build` 显式触发，并传递配置中的游戏目录：

```powershell
python tools/dev.py stages
python tools/dev.py build --output work/full-build
```

本轮只登记并接入原构建末尾阶段，保持先后顺序、函数、参数及结果映射。阶段仍会写相同文件，所以不推断可并行或可跳过的阶段，也不提供不安全的局部构建。专项验证已经可以独立运行。

## 测试与观察

先在 `.devtools.local.json` 中配置一个已验证的 `pdx_settings.json` 模板，也可使用 `--settings`。只复制设置，不复制账户、玩家存档或旧测试模组。

```powershell
# 默认只准备，不启动游戏
python tools/dev.py test --run-id affairs-check
python tools/dev.py run --run work/runs/affairs-check --timeout 300

# 或准备后直接执行短期受控测试
python tools/dev.py test --scenario tools/scenarios/affairs-balance.json --execute --timeout 300

# 自然观察：年限和检查点是参数，不再新建按日期命名的脚本
python tools/dev.py observe --years 20 --checkpoint-years 5 --run-id observe-20
python tools/dev.py run --run work/runs/observe-20 --timeout 7200
```

`run` 是前台监督命令，游戏进程使用无窗口启动。需要后台运行时，由调用方把这个稳定命令交给任务执行环境；不临时生成监督脚本。`status`、`stop` 可在另一个终端调用：

```powershell
python tools/dev.py status --run work/runs/observe-20
python tools/dev.py stop --run work/runs/observe-20
python tools/dev.py report --run work/runs/observe-20
```

每次运行有唯一目录，不覆盖旧证据。状态文件采用原子替换；同一目录不能启动两个监督器。停止时核对 PID、创建时间、可执行文件和精确的 `-userdir` 参数，再持有同一个 Windows 进程句柄终止，防止误杀复用 PID 的进程。不依赖 CIM 服务。

自然观察拒绝受控夹具；被动计数只加在副本中，不改变资源、研究、AI 权重或 RNG 抽取次数。项目表在准备时冻结。插桩要求已知脚本锚点全部匹配，失败时不写脚本；新玩法结构变化时更新适配器和测试。役负峰值读取检查点，不沿用旧测试中错误的峰值夹取计数。

场景 JSON 保存月份、检查点、测试名称、夹具映射和受控断言。夹具只允许仓库内源文件和测试模组内目标。`affairs-balance.json` 声明 12 项成功变量及 1 项失败标记缺失检查；断言从存档语义字段验证，不仅看日志文本。

## 报告与日志

报告默认写入 `<运行目录>/analysis/report.json` 和 `report.md`，同时记录：

- 目标日期、实际日期、缺失检查点和同一 playthrough 核验。
- 存续与消亡国家分开的累计贡献、逐国变化、完整语义快照与项目/性格计数。
- 登记诊断、脚本、GUI/本地化、资源及其他引擎消息的全部分组。
- 受控断言、引擎总测试结果、分析错误和崩溃文件，分别记录。

`report --receipt docs/testing/<名称>.json` 另写一份小型验收记录，保留检查点、断言、日志分类和失败状态，适合随代码提交。完整逐国数据和错误分组留在运行目录，不复制大文件到仓库。

用户停止、超时、进程失败、未达到目标和分析失败不能互相替代。分析成功不意味着游戏无错误。GUI 实际显示不由静态检查或存档分析推断为通过。

退出码：`0` 表示命令完成且未发现该命令明确检验的失败；`1` 表示验证失败（包括引擎总测试 FAIL）；`2` 表示配置、输入或工具执行错误。`not_fully_verified` 不能解释为全面通过。

```powershell
python tools/dev.py logs work/runs/observe-20/logs --output work/logs.json
python tools/dev.py logs work/runs/observe-20/logs --baseline work/logs.json --output work/log-diff.json
python tools/dev.py report --run work/runs/observe-20 --baseline work/logs.json
```

基线也可传完整报告 JSON。分组保留消息中的数值与国家信息；HBE 字样只是检索线索，原版路径也不自动归为无关错误。匹配到历史基线不代表已证明无害。初始加载与运行阶段的准确归因仍需结合上下文。

旧观察可直接用 `report --run <旧目录> --output <新输出目录>` 读取，兼容其 provenance 字段，不改写旧状态。`--cache` 可共享已有语义缓存。`--assertions-from <场景JSON>` 用于显式补充历史运行的断言定义，定义和来源会存入报告，不改写原场景证据。

## 打包与工坊

```powershell
python tools/dev.py package --output dist/release-candidate --report work/package.json --texconv C:/path/to/texconv.exe
python tools/dev.py release-plan --artifact dist/release-candidate --note-file docs/workshop_changelog_v040.txt --output work/release-plan.json
```

`package` 保留全部文件，复用现有 DDS 画质回退策略。输出目录不能已存在。`release-plan` 是本地操作，要求完整精简发行包，拒绝直接发布原始开发目录。发布计划冻结文件清单、大小、时间属性、manifest SHA 以及明确选择的说明文本；准备后文件变化即拒绝上传。常规冻结检测不额外重算所有 DDS hash，也不宣称能防御人为伪造文件属性。

只更新内容的计划不填 `--description`；只更新说明则不填 `--artifact`：

```powershell
python tools/dev.py release-plan --description schinese=docs/workshop_description_v040_schinese.bbcode --description english=docs/workshop_description_v040_english.bbcode --note-file docs/workshop_changelog_v040.txt --output work/text-plan.json

# 明确执行发布，需已有用户授权
python tools/dev.py publish --plan work/release-plan.json
python tools/dev.py verify-release --plan work/release-plan.json
```

SDK 使用已安装的 DLL、当前 Steam 身份和已有 Workshop 项目，不读取凭据或创建新项目。上传前核对项目归属。内容操作没有说明 setter，说明操作没有内容 setter；两者均没有标题、画廊和可见性的修改接口。回读配置中的所有语言，核对目标字段及其他字段保留情况。

发布意图先写盘，再上传；超时或部分失败记为 `outcome_unknown`，不自动重传同一计划。先运行 `verify-release` 查询实际结果，再决定后续处理。回读通过不等同于远端文件逐字节下载校验。当前不提供画廊上传命令，新增画廊编辑应另做明确范围的适配器。

## 美术与归档

```powershell
python tools/dev.py media --template tools/media/affairs-poster.json --output work/affairs-poster
python tools/dev.py archive --run work/runs/observe-20 --output outputs/observe-20-evidence.zip
```

宣传图模板记录底图、预期尺寸、截图/文字区域、裁切与背景；模板路径相对模板文件。代码嵌入真实截图，区域外像素必须保持一致。既有版本化宣传图脚本也调用共享排版函数。GUI 的真实字体、交互和布局仍需游戏内验收。

归档默认只含 provenance、冻结项目表、状态、运行输出、错误日志和报告，不含账户及缓存。只有显式 `--include-saves` 才收录存档；归档不自动删除测试目录。
