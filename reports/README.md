# 生成结果

运行 `python scripts/run_pipeline.py --config config/demo.toml` 后生成 `demo/`。
生成子目录默认不提交。每次运行更新四个固定文件；不保存逐条记录。
`run_manifest.json` 记录输入、配置、字典、代码、输出校验和及环境信息。
真实结果经独立审核后才可选择性发布；CI 仅执行合成数据演示。
