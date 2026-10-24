# 数据区域

`synthetic/participants.csv` 是手工编制的 12 条人工记录，不来自 NHANES 或任何患者资料。
ID 以 `DEMO_` 开头，周期固定为 `SYNTHETIC`。数值用于覆盖筛选和校验分支。

| 目录 | 约定 |
| --- | --- |
| `raw/` | 保留原文件，不覆盖；记录下载日期、来源、SHA-256 及使用条件 |
| `interim/` | 清洗、变量协调、合并检查的中间文件 |
| `processed/` | 按冻结方案生成的分析数据；记录来源与版本 |
| `synthetic/` | 经确认可公开的合成样例 |

前三个目录的内容默认不提交。Git 忽略不是保密机制：不要用 `git add -f` 绕过，也不要在 notebook、日志或报告中暴露个体数据。
详见 `docs/DATA_MANAGEMENT.md`。
