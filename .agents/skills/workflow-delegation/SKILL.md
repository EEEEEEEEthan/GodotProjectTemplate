---
name: workflow-delegation
description: 构造委派 prompt 模板。向 nahte 委派任务时，必须按此模板写清原因、需求、关键代码位置。
---

# Workflow 委派 Prompt 构造指南

向 nahte（workflow）委派任务时，prompt 必须包含以下三个部分，缺一不可。

## 模板

```
## 原因
（为什么需要做这个任务？背景是什么？解决了什么问题？）

## 需求
（具体要做什么？验收标准是什么？）

## 关键代码位置
（涉及哪些文件？路径是什么？相关函数/类名？）
```

## 示例

### ❌ 错误示例（太模糊）
```
运行 pylint 检查代码质量，选择一个值得优化的问题进行修复
```

### ✅ 正确示例
```
## 原因
agent_client.py 中存在未使用的 pathlib 导入，产生 lint 警告，影响代码整洁度。

## 需求
移除 agent_client.py 中未使用的 `import pathlib` 语句，确保 pylint 通过。

## 关键代码位置
- addons/egent/builtin/agent/agent_client.py 第 5 行：`import pathlib`
```

## 注意事项

- 三个部分缺一不可，nahte 需要完整上下文才能高效工作
- 代码位置要精确到行号或函数名
- 需求要可验证——nahte 完成后能明确判断是否达标
- 如果涉及多个文件，全部列出
