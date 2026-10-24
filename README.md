# Codex · 可复现研究代码骨架

面向 `jinxfjs/Codex` 的首个项目：**NHANES–MASLD 研究准备模板**。
当前版本可运行合成数据演示，提供数据管理、队列构建、描述统计、运行溯源和复现检查。
真实研究的周期、研究问题、MASLD 操作性定义及统计模型尚未确定，见 [研究方案](docs/PROTOCOL.md)。

> `exposure_demo`、`outcome_demo` 是人工构造的二元标记，没有临床含义。
> 演示结果不得解释为 MASLD 诊断、患病率、关联效应或 NHANES 人群估计。

## 立即运行

推荐 Python **3.12.10**（CI 固定版本）；本地另验证了 3.12.14。代码要求 Python 3.11 及以上。
仅使用标准库，不需要下载数据、联网或安装第三方依赖。在仓库根目录执行：

```sh
python --version
python scripts/run_pipeline.py --config config/demo.toml
python -m unittest discover -s tests -v
python scripts/verify_reproducibility.py
```

Windows 的 `python` 若未指向已安装版本，可替换为 `py -3.12`。
预期：12 条合成记录，经年龄缺失、演示年龄边界、暴露缺失和结局缺失筛选后保留 8 条。

| `reports/demo/` 输出 | 内容 |
| --- | --- |
| `cohort_flow.csv` | 每步筛选前人数、排除人数和保留人数 |
| `descriptive.csv` | 未加权样本量、缺失数、均值及演示标记比例 |
| `report.md` | SYNTHETIC ONLY 简报 |
| `run_manifest.json` | 输入、配置、字典、代码与输出 SHA-256；Python 版本和 Git 提交号 |

## 目录与分析分层

```text
Codex/
├── config/                   # 可运行演示配置、真实研究配置模板
├── data/
│   ├── raw/                  # 原始数据；不提交
│   ├── interim/              # 清洗及跨周期协调数据；不提交
│   ├── processed/            # 分析数据；不提交
│   └── synthetic/            # 可公开的人工测试数据
├── metadata/                 # 数据字典、变量映射、来源登记模板
├── src/research_pipeline/
│   ├── config.py             # 00 配置与路径
│   ├── data.py               # 01 标准化 CSV 读取、字典校验
│   ├── cohort.py             # 02 顺序筛选及流转人数
│   ├── analysis.py           # 03 未加权合成数据描述统计
│   └── pipeline.py           # 04 报告与运行溯源
├── scripts/                  # 命令行入口、双运行复现检查
├── tests/                    # 异常输入、筛选、统计及端到端测试
├── docs/                     # 方案、统计计划、复现与扩展指南
├── reports/                  # 生成结果；不提交
├── notebooks/                # 探索入口说明
├── manuscript/               # 稿件与结果对应说明
└── .github/                  # CI、依赖更新与协作模板
```

## 迁移至真实研究

1. 填写 [PROTOCOL.md](docs/PROTOCOL.md) 和 [ANALYSIS_PLAN.md](docs/ANALYSIS_PLAN.md)，明确问题、周期、结局、暴露、混杂因素和缺失处理。
2. 复制 `metadata/*.template.csv`，逐周期登记来源、原变量、单位、缺失码及转换规则。
3. 按 [DATA_MANAGEMENT.md](docs/DATA_MANAGEMENT.md) 在本地管理数据。
4. 按 [ADAPTATION.md](docs/ADAPTATION.md) 添加真实数据读取、变量协调、临床定义及复杂抽样分析模块与验证。
5. 完成真实分析后锁定新增依赖、保存运行清单，将论文表图与脚本对应。

`config/study.example.toml` 是设计模板，当前执行器会拒绝真实数据模式。
现有脚本只读取人工编制的标准化演示 CSV；尚未实现 XPT 下载、跨周期合并、MASLD 表型、调查加权推断或回归模型。
NHANES 权重选择、跨周期合并及设计变量应依据 [CDC 权重教程](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx) 和 [抽样设计教程](https://wwwn.cdc.gov/nchs/nhanes/tutorials/sampledesign.aspx)，逐研究确认。

## 获取代码与提交修改

从 GitHub 获取代码：

```sh
git clone https://github.com/jinxfjs/Codex.git
cd Codex
```

修改前创建分支，完成修改并验证后提交：

```sh
git switch -c research/your-change
# 完成修改并运行测试
git add .
git diff --cached --stat
git diff --cached --check
git status --short
git commit -m "Describe the research workflow change"
git push -u origin HEAD
```

随后在 GitHub 提交 PR。提交前检查暂存内容；远端有更新时先整合。
Git 作者姓名和邮箱使用研究者自己的配置。尚未选择开源许可证，由仓库所有者决定授权方式。
复现细节见 [REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)，协作流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。
