\# AUTO\_CALIBRATION.md



\## 1. 目的



本项目包含一套\*\*自动校准系统\*\*，用于在不同机器、不同输入环境下自动测量运行时动作参数，减少手工调参成本。



当前自动校准主要覆盖两个参数：



\- `TURNBACKSTEP`：默认转向步数

\- `METER`：默认前进 1 格所需按键持续时间



这两个参数原本来源于 `config.py`，现在支持通过校准结果文件在运行时覆盖。



\---



\## 2. 解决的问题



直接把参数写死在 `config.py` 中会有这些问题：



\- 不同机器上 `METER` 常常不一致

\- `TURNBACKSTEP` 也可能受鼠标步长、帧间隔、输入响应影响

\- 如果继续人工反复试错，效率低且不稳定



因此引入自动校准机制：



1\. 启动前自动检测是否已有校准文件

2\. 没有时可询问用户是否立即校准

3\. 校准完成后保存结果

4\. 后续运行自动读取并覆盖默认参数



\---



\## 3. 涉及文件



\### 3.1 `calibration.py`

自动校准逻辑主文件，负责：



\- 校准 `TURNBACKSTEP`

\- 校准 `METER`

\- 加载/保存校准结果

\- 输出校准日志与复验结果



核心接口：



\- `load\_calibration\_result()`

\- `save\_calibration\_result(result)`

\- `run\_full\_calibration(controller, state\_reader, verbose=True)`



\---



\### 3.2 `runtime\_params.py`

运行时参数桥接层，负责：



\- 先读取 `config.py` 默认值

\- 再读取 `runtime\_calibration.json`

\- 若校准文件存在，则覆盖默认值



核心接口：



\- `build\_runtime\_params()`



返回对象：



```python

RuntimeParams(

&#x20;   turnbackstep=...,

&#x20;   meter=...,

&#x20;   source="config" | "runtime\_calibration.json"

)

```



\---



\### 3.3 `controller.py`

已接入运行时参数。



当前设计中：



\- `Controller(runtime\_params=...)`

\- 默认动作不再依赖函数定义时绑定的 `config` 常量

\- 改为在运行时从实例属性读取：

&#x20; - `self.turnbackstep`

&#x20; - `self.meter`



典型形式：



```python

def look\_right(self, steps=None):

&#x20;   if steps is None:

&#x20;       steps = self.turnbackstep

```



```python

def move\_forward(self, press\_time=None):

&#x20;   if press\_time is None:

&#x20;       press\_time = self.meter

```



\---



\### 3.4 `builder\_actions.py`

已接入完成。  

只要它调用的是 `controller` 的默认动作，就会继承校准参数。



\---



\### 3.5 `main\_row.py`

已接入完成。负责：



\- 启动时检查校准文件是否存在

\- 若不存在，询问是否自动校准

\- 再构造 `runtime\_params`

\- 打印当前实际生效参数

\- 把参数传给 `Controller`



\---



\## 4. 校准结果文件



文件名：



```python

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



字段说明：



\- `turnbackstep`：校准出的默认转向步数

\- `meter`：校准出的默认前进时长

\- `updated\_at`：保存时间戳



\---



\## 5. 校准逻辑的基本假设



\### 5.1 reset 朝向假设

执行：



```python

controller.reset\_view\_ctrlzx()

```



后，理想朝向近似为：



```python

(face\_x, face\_z, face\_w) \~= (0, 1, 0)

```



即默认\*\*面向 +z\*\*。



\---



\### 5.2 `TURNBACKSTEP` 校准目标

在 reset 后执行：



```python

controller.look\_right(step)

```



目标是让朝向尽量接近：



```python

(face\_x, face\_z, face\_w) \~= (0, -1, 0)

```



即从 `+z` 转到 `-z`。



误差越小越好。



\---



\### 5.3 `METER` 校准目标

在 reset 后执行：



```python

controller.move\_forward(meter\_value)

```



记录动作前后位置差，目标是让位移尽量接近：



```python

dx \~= 0

dz \~= 1

dw \~= 0

```



即默认朝向下向前移动约 1 格。



\---



\## 6. `calibration.py` 的工作方式



\### 6.1 数据结构

使用：



```python

CalibrationResult

```



包含：



\- `turnbackstep`

\- `meter`

\- `updated\_at`



\---



\### 6.2 持久化接口



\- `load\_calibration\_result()`

\- `save\_calibration\_result(result)`



默认读写 `runtime\_calibration.json`。



\---



\### 6.3 `TURNBACKSTEP` 校准流程



主要函数：



\- `evaluate\_turnbackstep\_once(...)`

\- `verify\_turnbackstep(...)`

\- `calibrate\_turnbackstep(...)`



流程：



1\. reset 到统一朝向

2\. 测试多个候选 step

3\. 读取动作后朝向

4\. 计算与目标 `(0, -1, 0)` 的误差

5\. 先粗搜，再细搜

6\. 选出最佳值后做复验



误差大意：



```python

abs(fx - 0.0) + abs(fz + 1.0) + abs(fw - 0.0)

```



\---



\### 6.4 `METER` 校准流程



主要函数：



\- `evaluate\_meter\_once(...)`

\- `evaluate\_meter\_average(...)`

\- `verify\_meter(...)`

\- `calibrate\_meter(...)`



流程：



1\. reset 到统一朝向

2\. 读取起始位置

3\. 前进指定时长

4\. 读取结束位置

5\. 计算位移 `(dx, dz, dw)`

6\. 使用平均误差选择最佳候选

7\. 最终做复验



误差大意：



```python

abs(dz - 1.0) + abs(dx) + abs(dw)

```



\---



\### 6.5 总入口



```python

run\_full\_calibration(controller, state\_reader, verbose=True)

```



执行顺序：



1\. 校准 `TURNBACKSTEP`

2\. 校准 `METER`



返回：



```python

CalibrationResult

```



\---



\## 7. 第二版改进点



自动校准后来升级到第二版，重点改进如下。



\### 7.1 `METER` 同分裁决

细搜时可能出现多个候选平均误差完全相同，例如：



\- `0.23 -> 0.0`

\- `0.24 -> 0.0`



此时不再简单取较小值，而是：



1\. 优先选择\*\*更接近粗搜最佳值\*\*的候选

2\. 若距离也相同，再选较小值



这样结果更符合实际，也更稳定。



\---



\### 7.2 最终复验

增加了：



\- `verify\_turnbackstep(...)`

\- `verify\_meter(...)`



作用：



\- 对最终结果再重复测试若干次

\- 打印每次误差/位移

\- 统计平均误差与最大误差



提高可信度。



\---



\## 8. 状态读取原则



为了避免 `state\_reader` 的历史缓存干扰，每次校准测试前都采用统一流程：



1\. `state\_reader.reset\_history()`

2\. `controller.reset\_view\_ctrlzx()`

3\. 等待稳定

4\. 再 `state\_reader.reset\_history()`

5\. 再读取可信状态



辅助函数逻辑可概括为：



```python

\_reset\_and\_read\_state(controller, state\_reader)

```



这是保证校准稳定性的关键步骤。



\---



\## 9. 为什么不能只改 `config.py`



如果代码中有这种写法：



```python

def look\_right(self, steps=TURNBACKSTEP):

```



这里的默认值在\*\*函数定义时就绑定\*\*了。  

后续即使修改：



```python

config.TURNBACKSTEP = ...

```



也不会影响已定义好的默认参数。



因此自动校准接入的正确做法是：



\- 不再依赖 `def xxx(arg=TURNBACKSTEP/METER)`

\- 改为 `None` 占位

\- 在函数内部读取实例属性



例如：



```python

def look\_right(self, steps=None):

&#x20;   if steps is None:

&#x20;       steps = self.turnbackstep

```



\---



\## 10. 当前接入情况



目前已确认接入完成的文件：



\- `main\_row.py`

\- `controller.py`

\- `builder\_actions.py`



说明：



\- 主程序入口能自动发现/生成校准文件

\- `Controller` 默认动作已使用运行时参数

\- 建造动作链路已能继承校准结果



\---



\## 11. `main\_row.py` 当前行为



启动时：



1\. 调用 `ensure\_calibration\_file()`

2\. 检查 `runtime\_calibration.json` 是否存在

3\. 若不存在，则询问用户是否立即校准

4\. 校准完成后保存结果

5\. 然后调用 `build\_runtime\_params()`

6\. 打印参数来源、`TURNBACKSTEP`、`METER`

7\. 用这些参数初始化 `Controller`



典型日志：



```python

\[main\_row] 参数来源 = runtime\_calibration.json

\[main\_row] TURNBACKSTEP = 13

\[main\_row] METER = 0.24

```



若用户跳过校准，则可能显示：



```python

\[main\_row] 参数来源 = config

```



\---



\## 12. 使用约束



\### 12.1 不要显式传旧常量

尽量不要再写：



```python

controller.look\_right(config.TURNBACKSTEP)

controller.move\_forward(config.METER)

```



因为这会绕过运行时校准值。



应优先写成：



```python

controller.look\_right()

controller.move\_forward()

```



除非明确需要某个特殊动作值。



\---



\### 12.2 校准结果属于运行前准备

当前设计不是运行中动态学习，而是：



\- 启动时检测/补齐校准

\- 运行中固定使用本次启动时确定的参数



\---



\### 12.3 校准环境要求

自动校准时应保证：



1\. 角色站在平整地面

2\. 周围无遮挡、无障碍

3\. 前方有足够直线空间

4\. 不会掉落、撞墙、上坡或下坡

5\. reset 后朝向稳定



尤其 `METER` 对场地敏感。



\---



\## 13. 快速记忆版



如果以后要快速恢复这套系统，只需要记住下面几点：



\### 13.1 功能

自动校准两个参数：



\- `TURNBACKSTEP`

\- `METER`



\---



\### 13.2 文件

\- `calibration.py`：校准逻辑

\- `runtime\_params.py`：默认值 + 校准值合并

\- `runtime\_calibration.json`：校准结果文件



\---



\### 13.3 总入口

```python

run\_full\_calibration(controller, state\_reader)

```



\---



\### 13.4 运行时接入

\- `Controller(runtime\_params=...)`

\- 默认动作使用 `self.turnbackstep` / `self.meter`

\- 不再依赖静态默认参数绑定 config



\---



\### 13.5 主程序行为

`main\_row.py` 启动时：



\- 若无校准文件，询问是否自动校准

\- 然后 `build\_runtime\_params()`

\- 再把结果传给 `Controller`



\---



\## 14. 最短备注版



```markdown

本项目有自动校准系统，用于测量 TURNBACKSTEP 和 METER。



\- calibration.py

&#x20; - run\_full\_calibration(controller, state\_reader)

&#x20; - load\_calibration\_result()

&#x20; - save\_calibration\_result()

&#x20; - 结果保存在 runtime\_calibration.json



\- runtime\_params.py

&#x20; - build\_runtime\_params()

&#x20; - 先读 config.py，再用 runtime\_calibration.json 覆盖

&#x20; - 返回 RuntimeParams(turnbackstep, meter, source)



\- controller.py

&#x20; - 已接入运行时参数

&#x20; - look\_right/look\_left/look\_up/look\_down 默认用 self.turnbackstep

&#x20; - move\_forward 默认用 self.meter

&#x20; - 不再依赖 def xxx(arg=TURNBACKSTEP/METER)



\- main\_row.py

&#x20; - 启动时如果没有 runtime\_calibration.json，会询问是否自动校准

&#x20; - 然后 build\_runtime\_params() 并传给 Controller



\- builder\_actions.py

&#x20; - 已接入，动作链路可继承校准值



校准约定：

\- reset\_view\_ctrlzx() 后默认朝向约为 +z

\- TURNBACKSTEP：寻找从 +z 转到 -z 的最佳 look\_right(step)

\- METER：寻找默认朝向下前进一步约等于 1 格的 press\_time

```



\---



\## 15. 备注



已知旧代码中可能仍存在类似：



```python

def move\_forward(self, t=METER):

```



或直接显式使用 `METER`/`TURNBACKSTEP` 常量的写法。  

如果未来发现某些动作没有生效校准值，应优先检查这些位置并改为运行时参数读取方式。

