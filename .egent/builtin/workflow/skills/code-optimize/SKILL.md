---
name: code-optimize
description: 代码优化通用原则——减少字段/属性/方法的数量以降低维护成本。这是语言无关的优化手段。
---

# 代码优化：减少字段/属性/方法

## 核心原则

**维护成本 ∝ 状态数量 × 修改入口数量**

- **字段/属性** 是状态持有者。越多，越难推理程序当前处于什么状态。
- **方法** 是状态的修改入口。越多，越难追踪状态在哪里被改变。
- 每减少一个字段、属性或方法，就消除了一类潜在的 bug。

## 通用优化手段（语言无关）

### 1. 只被调用一次的方法 → 内联

如果一个方法在整个代码库中只被调用过一次，就不应该封装成独立方法。直接内联到调用处。

```
// ❌ 只被调用一次，多余的封装
function calculateDiscount(price) {
    return price * 0.1;
}
finalPrice = price - calculateDiscount(price);

// ✅ 直接内联
finalPrice = price - price * 0.1;
```

### 2. 只被同一个方法调用 → 内部方法

如果一个方法只被另一个方法调用（且调用者也只有一处），它应该成为调用者的内部方法/局部函数。

```
// ❌ 两个方法，两个修改入口
class Order {
    function process() {
        this.validateItems();
        // ...
    }
    function validateItems() {  // 只被 process 调用
        // ...
    }
}

// ✅ 一个方法，一个修改入口
class Order {
    function process() {
        function validateItems() {  // 内部函数
            // ...
        }
        validateItems();
        // ...
    }
}
```

### 3. 合并相关字段 → 数据类/结构体

多个字段总是一起出现、一起传递，说明它们是一个概念。

```
// ❌ 三个字段散落各处
self.x: float
self.y: float
self.z: float

// ✅ 一个字段，语义清晰
self.position: Vector3
```

### 4. 不访问实例状态的方法 → 模块级函数

如果一个方法不读取也不修改 `self`/`this` 的任何字段，它就不属于这个类。

```
// ❌ 方法但不访问 this
class Parser {
    normalize(text: string): string {
        return text.trim().toLowerCase();
    }
}

// ✅ 模块级函数，减少方法数
function normalize(text: string): string {
    return text.trim().toLowerCase();
}
```

### 5. 消除不必要的 getter/setter

如果 getter/setter 没有额外逻辑（校验、计算、副作用），直接用公开字段。

```
// ❌ 无逻辑的 getter
private _name: string;
getName(): string { return this._name; }

// ✅ 公开字段
name: string;
```

### 6. 只用过一次的常量/字符串 → 硬编码

如果一个常量、字符串字面量、配置值在整个代码库中只出现一次，不要提取为 const / 常量 / 配置项。直接硬编码在使用处。

提取成常量的意义在于**复用**和**统一修改点**。如果只被用了一次，就不存在复用，也没有"改一处漏一处"的风险。提取出去反而增加了间接层——阅读代码时多一次跳转，修改时多一个文件要碰。

```
// ❌ 只用了一次，多余的常量
const MAX_RETRY_COUNT = 3;
for (let i = 0; i < MAX_RETRY_COUNT; i++) { ... }

// ✅ 直接硬编码
for (let i = 0; i < 3; i++) { ... }
```

## 思考顺序

优化一个类时，按以下顺序审视：

1. **有没有只被调用一次的方法？** → 内联
2. **有没有只被一个方法调用的方法？** → 变成内部方法
3. **有没有只用过一次的常量/字符串？** → 硬编码
4. **有没有不碰 this 的方法？** → 提取为模块级函数
5. **有没有无逻辑的 getter/setter？** → 改为公开字段
6. **有没有总是一起出现的字段？** → 合并为数据类
7. **类是否承担了多个职责？** → 拆分
