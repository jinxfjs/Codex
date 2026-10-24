# 复现说明

## 环境

验证版本为 Python 3.12.14，代码使用 Python 3.11 起提供的 `tomllib`。
运行与测试仅依赖标准库；`requirements.txt` 不包含待下载包。
`.python-version` 固定演示用解释器版本，CI 按该版本运行。新增真实分析依赖时另建精确版本锁定文件。

## 执行

在仓库根目录执行：

```sh
python scripts/run_pipeline.py --config config/demo.toml
python -m unittest discover -s tests -v
python scripts/verify_reproducibility.py
```

配置内路径始终相对仓库根目录解析。入口脚本也可从其他目录以完整路径调用。
输出可改为 `--output reports/demo_alternative`，只能指向 `reports/` 的子目录。
真实研究配置模板会以非零退出码拒绝执行。校验失败或筛选后无记录时，不创建本次结果。

## 预期演示结果

| 步骤 | 保留 |
| --- | ---: |
| 输入 | 12 |
| 年龄非缺失 | 11 |
| 年龄 ≥ 20（演示条件） | 10 |
| 暴露非缺失 | 9 |
| 结局非缺失 | 8 |

保留记录年龄均值为 47.375，人工暴露标记均值为 0.625，人工结局标记均值为 0.5。
sex 类别 F=3、M=4、缺失=1。均为未加权合成数据汇总，不能解释为医学结论。

## 校验和与溯源

`run_manifest.json` 包括：

- 原始演示 CSV、字典和实际配置文件的 SHA-256。
- `src/**/*.py` 与 `scripts/*.py` 的 SHA-256。
- 三个结果文件的 SHA-256、输入及保留人数。
- Python 实现与版本、流水线版本、Git 提交号及工作区是否有改动。

没有提交时 `git.commit` 为 null；不在独立 Git 仓库或无法读取 Git 时 Git 信息为 null。
即使工作区未提交，代码哈希仍记录所执行的文件。
不记录当前时间、绝对路径或输出目录名，因此同一代码、输入、配置、环境与 Git 状态下的两个运行应逐字节一致。

`verify_reproducibility.py` 在 `reports/` 下建立两个临时目录，比较全部四个输出后清理自身临时目录。
它验证重复运行一致性；不能代替外部方法验证，也不证明跨 Python 版本、不同代码或真实数据的统计结果正确。
本地未执行远端 GitHub Actions；工作流待首次推送后运行 Windows 与 Ubuntu 检查。

## 重跑与结果保留

同一输出目录中的四个固定文件会被更新，其他文件不清理。需要保留多次结果时使用不同的 `--output`。
输入文件只读，代码不修改 `raw/`，不导出逐行个体记录。
对正式研究，保存冻结配置、依赖、代码提交、数据来源登记和已审核的结果归档。
