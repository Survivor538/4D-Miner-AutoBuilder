可以，下面我直接给你一份\*\*可保存为项目总说明的 Markdown 文档\*\*。  

你可以把它保存成比如：



\- `README.md`

\- 或 `PROJECT\_OVERVIEW.md`



我会按\*\*当前项目真实结构\*\*来写，并把\*\*自动校准、导航、建造、断点恢复、配置参数、已知问题\*\*这些都纳入进去。



\---



\# 项目总说明（Markdown）



```md

\# 自动建造项目总说明



\## 1. 项目简介



本项目是一个基于游戏状态读取与输入控制的\*\*自动建造系统\*\*，用于在游戏中按照预定义结构自动完成导航、放置、拆除、断点恢复等操作。



项目的核心特点：



\- 读取玩家实时状态（位置、朝向等）

\- 自动导航到目标列位置

\- 自动执行单列建造/辅助柱处理

\- 支持断点保存与恢复

\- 支持运行前自动校准关键动作参数

\- 支持停止请求与安全退出



\---



\## 2. 当前功能状态



\### 已完成

\- 自动校准系统

&#x20; - `TURNBACKSTEP`

&#x20; - `METER`

\- 运行时参数加载

\- `Controller` 接入校准参数

\- `Navigator` 导航优化

\- `BuilderActions` 动作优化

\- 行级执行器（row executor）

\- 进度保存与断点恢复

\- 主流程入口 `main\_row.py`



\### 当前暂不做

\- `LEFTCLICKTIME` 自动校准

\- `JUMP\_PUT\_WAIT` 自动校准

\- 某些疑似未使用配置项的彻底清理（待进一步确认）

\- 个别导航异常（如 `\[step\_plus\_x] prepare plane 失败`）暂缓处理



\---



\## 3. 项目文件结构



\### 主流程相关

\- `main\_row.py`

&#x20; - 主入口

&#x20; - 负责整体流程调度

&#x20; - 包括结构生成、断点恢复、校准检查、上下文构建、执行构建等



\- `build\_entry.py`

&#x20; - 构建入口辅助脚本

&#x20; - 用于启动构建流程或封装主程序调用



\---



\### 自动校准相关

\- `calibration.py`

&#x20; - 自动校准逻辑

&#x20; - 当前主要校准：

&#x20;   - `TURNBACKSTEP`

&#x20;   - `METER`

&#x20; - 支持读取/保存校准结果



\- `runtime\_params.py`

&#x20; - 运行时参数桥接

&#x20; - 负责：

&#x20;   - 从 `config.py` 读取默认参数

&#x20;   - 从 `runtime\_calibration.json` 读取校准值

&#x20;   - 返回最终运行参数对象



\---



\### 输入控制相关

\- `controller.py`

&#x20; - 底层输入控制

&#x20; - 包括：

&#x20;   - 视角重置

&#x20;   - 左右/上下转向

&#x20;   - 前进

&#x20;   - 跳跃

&#x20;   - 左键/右键

&#x20;   - 选中物品栏物品



\---



\### 状态读取相关

\- `state\_reader.py`

&#x20; - 读取玩家当前状态

&#x20; - 状态包括位置、朝向等

&#x20; - 为导航与建造提供判定依据



\- `data\_types.py`

&#x20; - 状态对象、结构对象等公共数据结构定义



\---



\### 导航相关

\- `navigator.py`

&#x20; - 负责移动到指定 `(x, z, w)` 位置

&#x20; - 支持：

&#x20;   - 单步移动

&#x20;   - 多步移动

&#x20;   - 视角平面切换

&#x20;   - 连续移动中的周期性重校正

&#x20; - 已做过动作优化，减少重复 reset



\---



\### 建造动作相关

\- `builder\_actions.py`

&#x20; - 负责具体的建柱、拆柱、辅助柱等动作

&#x20; - 使用 `Controller + Navigator + StateReader`

&#x20; - 已做过动作优化，减少重复 reset，提升连续动作效率



\---



\### 结构与规划相关

\- `structure.py`

&#x20; - 结构数据定义或结构生成辅助



\- `planner.py`

&#x20; - 将结构拆分为逐行/逐列任务

&#x20; - 供执行器按顺序处理



\---



\### 执行与进度相关

\- `row\_executor.py`

&#x20; - 行级执行器

&#x20; - 负责按行推进建造过程

&#x20; - 调用 `BuilderActions` 完成列处理

&#x20; - 与进度系统、停止控制联动



\- `progress.py`

&#x20; - 进度保存、读取、清理

&#x20; - 用于断点恢复



\- `stop\_control.py`

&#x20; - 停止控制

&#x20; - 当前支持通过热键请求停止（如 F8）



\---



\### 工具类

\- `utils.py`

&#x20; - 通用辅助函数



\---



\### 配置文件

\- `config.py`

&#x20; - 项目全局参数配置

&#x20; - 包括输入动作参数、导航参数、恢复参数、日志参数等



\---



\## 4. 项目运行流程



项目整体运行流程如下：



1\. 启动主程序 `main\_row.py`

2\. 检查校准文件是否存在

3\. 构建运行时参数 `runtime\_params`

4\. 构建上下文：

&#x20;  - `Controller`

&#x20;  - `StateReader`

&#x20;  - `Navigator`

&#x20;  - `BuilderActions`

&#x20;  - `ProgressManager`

5\. 生成或读取目标结构

6\. 检查是否从断点恢复

7\. 启动停止控制

8\. 执行逐行构建

9\. 每行/每列根据需要保存进度

10\. 构建完成后清理进度文件



\---



\## 5. 自动校准系统说明



\### 5.1 当前已校准参数



\#### `TURNBACKSTEP`

表示默认一次转向所需的鼠标步数，用于：



\- `look\_right()`

\- `look\_left()`



其目标是：

\- 在 `reset\_view\_ctrlzx()` 后

\- 执行 `look\_right(step)`

\- 使朝向从 `+z` 尽量转到 `-z`



\---



\#### `METER`

表示默认前进一步所需的按键持续时间，用于：



\- `move\_forward()`



其目标是：

\- 在 reset 后面向 `+z`

\- 前进一次

\- 位移尽量接近 1 格



\---



\### 5.2 校准结果文件



校准结果保存于：



```json

runtime\_calibration.json

```



示例：



```json

{

&#x20; "turnbackstep": 13,

&#x20; "meter": 0.24,

&#x20; "updated\_at": 1776305194.8956141

}

```



\---



\### 5.3 运行时参数生效方式



运行时参数由 `runtime\_params.py` 统一构建：



1\. 先读取 `config.py` 默认值

2\. 再读取 `runtime\_calibration.json`

3\. 若校准值存在，则覆盖默认值



最终注入到 `Controller` 中，避免继续依赖静态默认参数。



\---



\## 6. 导航系统说明



`navigator.py` 负责把角色移动到目标坐标位置。



\### 6.1 导航特征

\- 支持 `x / z / w` 方向移动

\- 支持按平面切换视角（如 `zx` / `zw`）

\- 支持单步验证

\- 支持长距离移动中的周期性重校正



\### 6.2 已做的优化

\- 不再每一步都强制 reset

\- 引入视角平面缓存

\- 连续移动时每隔若干步重新校正

\- 优先利用已有的有效状态数据



\### 6.3 当前已知问题

有时会出现类似：



```text

\[step\_plus\_x] prepare plane 失败

```



这说明在执行某个单步前，导航器未能成功准备到目标平面或未能完成视角准备。  

该问题目前\*\*已发现但尚未修复\*\*，后续排查重点可能包括：



\- reset 后状态读取不稳定

\- 平面准备逻辑过严

\- 状态历史缓存影响判断

\- 长距离移动后的姿态漂移



\---



\## 7. 建造动作系统说明



`builder\_actions.py` 负责具体的建造行为，是本项目最核心的动作层之一。



\### 7.1 主要职责

\- 清理动作姿态

\- 导航到列位置

\- 建造主柱

\- 建造辅助柱

\- 拆除辅助柱

\- 处理列间衔接动作



\### 7.2 已做的动作优化

\- 减少重复 reset

\- 连续建造时不再每一小步都重复做完整准备

\- 允许连续放置/连续拆除时减少冗余动作

\- 优化建造节奏，提高效率



\### 7.3 当前核心参数

\- `JUMP\_PUT\_WAIT`

\- `LOOK\_DOWN\_JUMP\_PUT\_RATIO`

\- `BREAK\_RATIO`

\- `BREAK\_WHOLE\_COLUMN\_LOOK\_DOWN\_RATIO`

\- `COLUMN\_ACTION\_INTERVAL`

\- `COLUMN\_FINISH\_WAIT`



其中 `JUMP\_PUT\_WAIT` 对跳搭是否稳定尤其重要。



\---



\## 8. 断点恢复与进度系统



项目支持断点恢复。



\### 8.1 进度文件

默认进度文件：



```python

progress.json

```



\### 8.2 保存粒度

由配置项控制：

\- 是否每行保存

\- 是否每列保存



\### 8.3 恢复机制

恢复时会检查：

\- 结构是否一致

\- 进度是否可用

\- 玩家是否处于可继续执行的位置附近



\---



\## 9. 停止控制



项目支持运行中请求停止。



\### 9.1 当前方式

\- 使用热键（如 F8）请求停止



\### 9.2 停止原则

\- 不一定立即中断

\- 程序会尽量在安全点停下

\- 停止时保存断点，便于后续恢复



\---



\## 10. `config.py` 参数分类说明



当前 `config.py` 中的参数大致可分为以下几类。



\---



\### 10.1 基础控制参数

用于动作控制的核心参数：



\- `TURNBACKSTEP`

\- `METER`

\- `LEFTCLICKTIME`

\- `RIGHTCLICKTIME`

\- `BREAK\_PRESS\_TIME`

\- `RESET\_WAIT`

\- `MOVE\_WAIT`

\- `JUMP\_PUT\_WAIT`



说明：

\- `TURNBACKSTEP`、`METER` 支持自动校准覆盖

\- `LEFTCLICKTIME` 当前仍由配置控制，未自动校准



\---



\### 10.2 物品栏参数

用于选择方块和工具：



\- `DEADLYPICK`

\- `STONE`



\---



\### 10.3 建造动作参数

用于控制放置、拆除、节奏与角度：



\- `BLOCK\_PLACE\_INTERVAL`

\- `BLOCK\_BREAK\_INTERVAL`

\- `COLUMN\_ACTION\_INTERVAL`

\- `COLUMN\_FINISH\_WAIT`

\- `LOOK\_DOWN\_JUMP\_PUT\_RATIO`

\- `BREAK\_RATIO`

\- `BREAK\_WHOLE\_COLUMN\_LOOK\_DOWN\_RATIO`



以及动作优化相关项：



\- `BUILD\_RESET\_EVERY\_N\_BLOCKS`

\- `BREAK\_RESET\_EVERY\_N\_BLOCKS`

\- `JUMP\_PUT\_POST\_CLICK\_WAIT`

\- `COLUMN\_FINAL\_PLACE\_SETTLE\_WAIT`



\---



\### 10.4 导航动作参数

用于长距离移动和重校正：



\- `LONG\_MOVE\_RENORMALIZE\_EVERY`

\- `LONG\_MOVE\_RESET\_EVERY`



\---



\### 10.5 辅助柱参数

用于辅助柱逻辑：



\- `AUXILIARY\_Z\_OFFSET`

\- `AUXILIARY\_ENABLED`

\- `SLEEP\_AFTER\_AUX\_COLUMN`



\---



\### 10.6 状态读取与校验参数

用于状态读取和连续性判断：



\- `READ\_RETRY\_TIMES`

\- `READ\_RETRY\_INTERVAL`

\- `GRID\_CENTER\_TOLERANCE`

\- `FACE\_TOLERANCE`

\- `MAX\_CONTINUITY\_DELTA\_X`

\- `MAX\_CONTINUITY\_DELTA\_Y`

\- `MAX\_CONTINUITY\_DELTA\_Z`

\- `MAX\_CONTINUITY\_DELTA\_W`

\- `MAX\_RECOVER\_RETRY`

\- `MAX\_STATE\_FAIL\_BEFORE\_ABORT`



\---



\### 10.7 进度与恢复参数

用于断点保存与恢复：



\- `PROGRESS\_FILE`

\- `SAVE\_PROGRESS\_EVERY\_ROW`

\- `SAVE\_PROGRESS\_EVERY\_COLUMN`

\- `ENABLE\_RESUME`

\- `REQUIRE\_STRUCTURE\_HASH\_MATCH`



\---



\### 10.8 运行节奏参数

用于主流程节奏控制：



\- `START\_DELAY\_SECONDS`

\- `SLEEP\_BETWEEN\_COLUMNS`

\- `SLEEP\_BETWEEN\_ROWS`

\- `BREAK\_AUXILIARY\_AFTER\_ROW`



\---



\### 10.9 调试与日志参数

用于输出调试信息：



\- `DEBUG`

\- `PRINT\_STATE\_READ`

\- `PRINT\_NAVIGATION\_DETAIL`

\- `PRINT\_BUILD\_DETAIL`

\- `PRINT\_PROGRESS\_DETAIL`



\---



\## 11. 当前已确认的重要事实



\### 11.1 自动校准系统已经完成

已完成并接入：

\- `calibration.py`

\- `runtime\_params.py`

\- `controller.py`

\- `main\_row.py`

\- `builder\_actions.py`



\---



\### 11.2 动作优化已经完成

已完成的动作优化主要包括：

\- `builder\_actions.py`

\- `navigator.py`



当前可以将它们视为已完成的底层动作模块。



\---



\### 11.3 当前上传的文件版本是最新参考

如果与更早版本或旧讨论记录冲突，应以当前上传文件为准。



\---



\## 12. 当前已知待办事项



\### 高优先级

\- 整理 `config.py`，删除未使用参数

\- 检查全项目是否存在重大逻辑问题

\- 排查 `\[step\_plus\_x] prepare plane 失败` 的成因



\### 中优先级

\- 提升主流程鲁棒性

\- 增加更多验证脚本

\- 梳理参数实际引用关系



\### 低优先级 / 暂缓

\- `LEFTCLICKTIME` 自动校准

\- `JUMP\_PUT\_WAIT` 自动校准



\---



\## 13. 使用说明（简化版）



\### 运行前准备

1\. 确保角色位于适合开始建造的位置

2\. 确保地面平整、无遮挡

3\. 确保物品栏中：

&#x20;  - 方块位于设定槽位

&#x20;  - 工具位于设定槽位

4\. 若没有 `runtime\_calibration.json`，可先进行自动校准



\### 启动程序

运行：



```bash

python main\_row.py

```



\### 运行过程

\- 启动后根据提示切回游戏窗口

\- 程序会自动读状态、导航、建造

\- 运行中可按 F8 请求停止



\---



\## 14. 后续维护建议



1\. 先梳理 `config.py` 实际引用项

2\. 清理无效参数，避免后续混淆

3\. 对 `navigator.py` 的 prepare-plane 问题做专项排查

4\. 建立最小测试脚本：

&#x20;  - 单步导航测试

&#x20;  - 单列建造测试

&#x20;  - 辅助柱拆除测试

&#x20;  - 断点恢复测试

5\. 若后续稳定，再考虑扩展更多自动校准参数



\---



\## 15. 一句话总结



这是一个已经具备：



\- 自动校准

\- 导航

\- 建造

\- 断点恢复

\- 安全停止



能力的自动建造项目。  

当前重点已经从“搭建系统”转向“清理配置、排查边缘问题、提升稳定性”。



```



\---





