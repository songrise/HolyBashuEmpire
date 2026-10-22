# EU5 存档语义读取工具

后续查询存档优先使用本工具及其库接口。不要复制正则去扫描整份原始存档，也不要再为每次观察生成一份独立解析脚本。

## 分层与复用

`tools/eu5save` 是独立包，只有标准库依赖，不加载游戏、不改写存档。

|模块|职责|
|---|---|
|`source.py`|只读mmap、SAV文本头、UTF-8/BOM、有限大小的ZIP文本存档、输入变化检测|
|`syntax.py`|按需解析语法树，保留重复键、顺序、匿名列表、运算符、引号和标签块|
|`eu5.py`|EU5国家、组织、建筑、兵种、战争、市场及原生变量类型|
|`hbe.py`|HBE成员、地方事业、测试计数、项目和异常检查；标签与名称由manifest提供|
|`cache.py`|版本化语义缓存，原子写入，损坏后重建|
|`cli.py`|统一查询命令，结构化JSON输出与非零失败码|

通用层不写死巴蜀国家列表，也不将所有数据库当成同一种结构。HBE层选取当前帝国成员及manifest中的原始诸侯，保留消亡记录。其他模组可以复用 `EU5Save` 的通用接口并提供自己的语义投影，无需修改底层语法解析。

## 命令行

在仓库根目录运行。Windows PowerShell 中可先设置 `$env:PYTHONIOENCODING='utf-8'`。

```powershell
# 首次读取后建立语义缓存；后续命令使用缓存
python tools/save_query.py summary 'D:/saves/example.eu5'
python tools/save_query.py country 'D:/saves/example.eu5' BAP --alive --fields tag,name,gold,affairs.budget,affairs.completed
python tools/save_query.py projects 'D:/saves/example.eu5'
python tools/save_query.py check 'D:/saves/example.eu5'

# PowerShell不展开引号内通配符；工具自行展开并按游戏日期排序
python tools/save_query.py --output work/timeline.json timeline 'D:/saves/scheduled*.eu5'

# 导出完整语义数据；也支持 python -m tools.eu5save
python tools/save_query.py --output work/snapshot.json snapshot 'D:/saves/example.eu5'
```

全局选项必须放在命令名前：`--manifest`、`--catalogue`、`--cache`、`--no-cache`、`--refresh`、`--output`。

`timeline` 默认拒绝跨playthrough的混合存档；有意比较不同局时使用 `--allow-mixed`。同名国家有多个历史实例时，`country` 返回全部匹配项，可用 `--alive` 或 `--id` 缩小范围，不会静默覆盖其中一条。

## 库接口

```python
from tools.eu5save import EU5Save, load_snapshot

with EU5Save('example.eu5') as game:
    print(game.metadata)
    for country in game.countries():
        print(country['tag'], country['gold'])
    print(game.goods())
    # 直接结构查询也遵守作用域，不会匹配到dead_countries等同名子串。
    values = game.root.block('countries').block('database').all('1209')

snapshot, cache = load_snapshot(
    'example.eu5',
    manifest='mod/holy_bashu_empire/build_manifest.json',
    cache_dir='work/save-cache',
)
```

低层Block/Scalar对象只能在源文档打开时使用；语义字典与缓存结果在文件关闭后仍可使用。`Block.one()` 遇到重复键抛出 `AmbiguousKey`；显式使用 `all()` 获取全部值。

## 稳健性约定

- 支持明文及带SAV头的EU5文本存档、包含文本gamestate的ZIP。真正的二进制或其他压缩编码会明确报 `UnsupportedFormat`，不会猜测解码、返回空数据或假装支持；请先用 `-force_text_save` 导出。
- ZIP不解压到文件系统，限制解压后大小，拒绝重复/歧义gamestate成员与加密成员。
- 未闭合块、未结束字符串、缺失赋值、重复数据库ID、冲突变量、无效布尔、异常固定小数和源文件变化均有类型化错误。库调用可捕获 `SaveError`；CLI输出JSON错误并返回2。
- 语法节点延迟展开；读取常用字段时仍检查所跨块的括号/字符串完整性。需要检查所有未知字段的语法时可调用 `game.validate()`，代价高于语义查询。
- 原生数据库 `id=none` 是已删除对象的占位；语法层保留它，活动记录接口跳过它。
- 变量 `type=value` 使用有符号64位、十万分之一精度；省略identity表示零。`data={}` 表示空变量，与数值零区分；引用类型保持类型和ID。缺少观测计数器返回null，不能冒充执行次数为0。
- 国家人口使用原生的千人单位。地方事业人口奖励计数器记录人数，不能直接相加。
- 缓存键包括绝对路径、文件大小、mtime/ctime纳秒、manifest身份及缓存/适配器版本；不在每次查询时对几百MB存档做哈希。语义版本变更时需递增 `CACHE_VERSION`。外部程序同时伪造所有文件身份属性不在轻量缓存保证范围内，可用 `--refresh` 强制重读。
- 不解析崩溃日志，不将存档状态检查当作游戏运行测试通过。项目计数为保留国家记录的口径；国家删除、释放或重建可能影响累计值。

## 验证

```powershell
python -m unittest discover -s tools -p test_eu5save.py -v

# 可选真实存档回归，复用已有观察JSON，不再另写原始解析器
$env:EU5_SAVE_REFERENCE='D:/observations/report.json'
$env:EU5_SAVE_DIR='D:/observations/save games'
python -m unittest discover -s tools -p test_eu5save_integration.py -v
```

首次完整HBE投影比旧的定向正则慢，但作用域与错误处理完整；同一存档的后续国家、项目、时间线查询走持久缓存。实测值及真实检查点对照结果记在 `docs/testing/save-parser-v040.json`。
