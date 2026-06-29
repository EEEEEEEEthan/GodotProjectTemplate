# agent

## import 规范

**除 `from __future__ import annotations` 外，禁止使用 `from ... import ...`。**

统一使用 `import 模块`，引用时写全限定名：

```python
# 可以
from __future__ import annotations

import pathlib
import agent.agent_events

path = pathlib.Path("foo")
event = agent.agent_events.TextDelta("hello")

# 不可以
from pathlib import Path
from agent.agent_events import TextDelta
```

### 说明

- `from __future__ import annotations` 是语言级特性，无法用 `__future__.annotations` 替代，因此保留。
- 包内互相引用同样遵循上述规则，例如 `import agent.agent_tools`，使用 `agent.agent_tools.TOOL_SCHEMAS`。
- `tools/__init__.py` 如需对外 re-export，用属性赋值，不要用 `from ... import ...`：

```python
import importlib

_file_edit_tool = importlib.import_module(".file_edit_tool", __name__)
FileEditTool = _file_edit_tool.FileEditTool
```
