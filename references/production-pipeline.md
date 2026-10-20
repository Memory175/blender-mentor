# 通用生产流程与门禁（V5.16.1）

> 适用：任何 Blender 建模、场景、室内、资产、程序化生成、批改与评审任务。
> 目标：把“看起来像”变成“可复现、可检查、可交付”。
> 本文件只定义流程；具体数值以模块/项目实测/当地规范为准。

## 0. 五条原则

```text
1. 先定规则，后生成几何
2. 单一数据源，不手写绝对坐标
3. 每层有验收门，过不了不进下一层
4. 自动检查优先于截图检查
5. 布局冻结后，表现层不许改几何
```

流程不是“多写文档”，而是**把返工点前移**：越早发现，改起来越便宜。

---

## 1. 七阶段与门禁

| 阶段 | 输入 | 输出 | 门禁 |
|---|---|---|---|
| G0 需求 | 参考图、用途、尺寸、风格、交付格式 | brief、范围、假设清单 | 需求/尺寸确认 |
| G1 规格 | brief | 轴网、房间表、门窗表、材质/相机清单 | 规格表通过 |
| G2 Blockout | 规格表 | 墙、门、窗、核心筒、空间标签 | 空间/门洞/拓扑通过 |
| G3 固定系统 | Blockout | 厨房、卫浴、衣帽间、楼梯、管井 | 部件级碰撞/净距通过 |
| G4 活动家具 | 固定系统 | 家具布置、2D 家具图 | 朝向/干涉/通道通过 |
| G5 表现层 | 冻结布局 | 材质、灯光、软装、相机、出图 | 相机/渲染/材质通过 |
| G6 交付 | 全部 | blend/glb/报告/清单 | 版本/导出校验 |

### G0 需求

先写清：

```text
用途：概念沟通 / 视觉出图 / 游戏资产 / 施工前模型 / 工程评审
范围：只做外观，还是含室内、结构表达、场地、导出
验收：尺寸、开口、材质、相机、文件格式
边界：哪些不做、哪些需要专业复核
```

**没有尺寸就标 `[ASSUMPTION]`，不能把猜测当实测。**

### G1 规格

至少产出：

```text
axis_grid.json             轴网、墙厚、层高
room_schedule.csv          房间、边界、面积、功能
door_window_schedule.csv   门窗、宽度、高度、铰链、开启方向
material_intent.md         材质意图，不定死贴图
camera_list.md             最终要出的视角
```

### G2 Blockout

只做墙、门、窗、核心筒、空间标签，**不放家具**。

必须通过：

```text
房间不重叠、在轮廓内
门窗在墙段内
门宽/门高合法
同墙开口不重叠
拓扑通过
```

### G3 固定系统

厨房、卫浴、衣帽间、楼梯、管井。

必须通过：

```text
部件级碰撞
门内侧净空
门扇开启弧
操作通道
烟道/吊柜/台面关系
```

### G4 活动家具

先出 **2D 家具布置图**，再落 3D。

必须通过：

```text
家具不越房间
家具组互不干涉
门洞 keep-out
椅背朝向
主通道
```

### G5 表现层

材质、灯光、软装、相机、出图。**不改布局坐标。**

必须通过：

```text
相机不穿墙/不穿玻璃/不穿家具
天花在平面图隐藏，室内图显示
标签只出现在平面图
每个空间至少 1 张主视角
无缺失材质/UV
```

### G6 交付

```text
final.blend / final.glb（按需 obj）
平面、轴测、空间主视角
README（尺寸、相机、检查、边界）
检查报告（含覆盖率）
复现命令/脚本
```

---

## 2. 标准目录

```text
project/
  00_input/
  01_spec/
    axis_grid.json
    room_schedule.csv
    door_window_schedule.csv
    assumptions.md
    material_intent.md
    camera_list.md
  02_blockout/
  03_fixed/
  04_furniture/
  05_presentation/
  06_delivery/
  scripts/
    core/       units / grid / walls / doors / placement
    checks/     data / topology / collision / door swing / export
    build_*.py
    render_*.py
  docs/
    SOP.md
    checklists/
    changelog.md
```

---

## 3. 数据契约

### 3.1 轴网

```json
{
  "unit": "m",
  "x_axes": [0, 2.2, 4.2],
  "y_axes": [0, 2.8, 3.6],
  "wall_exterior": 0.18,
  "wall_interior": 0.14
}
```

### 3.2 门窗

```json
{
  "id": "door_bath1",
  "wall": "bath_e",
  "center": 8.7,
  "width": 0.8,
  "height": 2.1,
  "hinge": "start",
  "swing": "in",
  "room_a": "bath1",
  "room_b": "corridor"
}
```

### 3.3 家具/固定件

```json
{
  "id": "Kitchen_Fridge",
  "room": "kitchen",
  "size": [0.62, 0.70, 2.0],
  "anchor": {
    "type": "wall_end",
    "wall": "north",
    "run": "Kitchen_North_Cab",
    "gap": 0.02
  },
  "support": "floor",
  "clearance": {"front": 0.9}
}
```

### 3.4 对象注册表

每个对象至少有：

```text
id / 类型 / 房间 / 父级 / 材质 / 支撑方式 / 净距规则 / 状态
```

禁止：

```text
同名批量对象
无父级散件
无房间归属
无净距定义
```

---

## 4. 摆放规则

位置由 helper 计算，不在业务脚本里写绝对坐标：

```text
place_against_wall()
place_at_end_of_run()
place_centered_in_room()
place_relative_to_door()
place_around_opening()
stack_on()
mount_on_wall()
```

示例：

```python
place_at_end_of_run(
    asset="Kitchen_Fridge",
    wall="north",
    run="Kitchen_North_Cab",
    gap=0.02
)
```

反例：

```python
box("Fridge", (3.76, 14.85, 1.0), ...)
```

---

## 5. QA 金字塔

| 层 | 检查 | 工具 |
|---|---|---|
| L0 | 数据/单位/轴网/门窗表 | JSON schema、Python 断言 |
| L1 | 拓扑 | manifold、loose、n-gon、normal、UV |
| L2 | 空间 | AABB 宽相位 → BVH/网格精确碰撞 |
| L3 | 使用 | 门扇扫掠、通道宽度、操作净距 |
| L4 | 表现 | 相机穿模、遮挡、曝光、材质缺失 |
| L5 | 导出 | GLB/OBJ 完整性、尺度、材质数 |

### 硬规则

```text
不允许静默 allowlist
不允许“同房间豁免”
允许的接触必须写 reason + owner + 过期时间
报告必须写覆盖率
0 FAIL 只有在覆盖率 100% 时才有效
```

允许接触示例：

```text
餐桌 ↔ 餐椅（椅子塞桌下）
床 ↔ 床头柜（贴床侧）
油烟机 ↔ 吊柜（吊装关系）
```

但必须是**显式例外表**，不能默认放宽。

### 覆盖率格式

```text
doors: 11/11 checked
fixed groups: 7/7
movable groups: 15/15
collision pairs: 128 checked / 0 unhandled
FAIL 0 / WARN 0
```

---

## 6. 冻结与变更控制

```text
v0.1 规格
v0.2 blockout
v0.3 fixed
v0.4 furniture
v0.5 presentation
v1.0 delivery
```

冻结后改轴网：

```text
改 axis_grid.json
→ 失效 downstream cache
→ 重建 blockout
→ 重建 fixed
→ 重建 furniture
→ 重跑全部检查
→ 重出图
```

禁止：

```text
只改 final.blend
只改一个家具位置
跳过检查直接出图
```

---

## 7. 评审与角色

最小角色：

```text
Layout Owner    轴网/门洞/空间
Asset Owner     固定件/家具
QA Owner        独立检查，不参与建模
Render Owner    表现层
```

单人项目按时间分开：

```text
第 1 天：只做 blockout + 检查
第 2 天：只做固定/活动家具 + 检查
第 3 天：只做表现层 + 出图
```

Agent/团队：

```text
一个写，一个只读审计
写作用域分开
校验脚本不与被检对象同一人维护
禁止自己改规则让自己通过
```

---

## 8. 反模式

```text
一次性堆几百个对象
先家具后墙门
手写绝对坐标
用截图代替数值检查
把真问题写进 allowlist
同房间豁免
布局没冻结就做材质灯光
最终图里改几何
没有版本/变更记录
```

---

## 9. Definition of Done

```text
□ 轴网/房间/门窗表已确认
□ Blockout 门宽/门洞/窗高/房间不重叠通过
□ 固定件部件级碰撞通过
□ 门内侧净空/门扇开启弧通过
□ 活动家具朝向/干涉/通道通过
□ 2D 家具图已确认
□ 命名无重复
□ 拓扑 0 non-manifold / 0 loose / 0 n-gon / 0 无 UV
□ 相机无穿模/无遮挡
□ 每个空间至少 1 张主视角
□ GLB/OBJ 导出校验通过
□ 报告写清覆盖率与剩余风险
```

---

## 10. 与现有文档接口

```text
SKILL.md §0.7          全局硬规则
references/model-qa.md 模型层检查
references/acceptance-profiles.md 验收分项与 profile
references/main.md §2.11 生产流程协议
references/module-int-*.md 室内布局校验
项目侧 layout_check.py 执行入口
```

> 流程不能替代实测、专业审图、结构/MEP/消防/无障碍/能耗合规。
