# 数据库 ER 图与表结构设计

> 系统采用轻量级 SQLite 存储，按「生产 / 测试 / 档案」三库分离管理，价格数据按线路分表（美线 / 欧线 / 加拿大线），从根上避免跨线路脏数据。

## 1. ER 图（Mermaid）

```mermaid
erDiagram
    SUPPLIERS ||--o{ CHANNELS : "拥有"
    SUPPLIERS ||--o{ PRICES : "报价"
    SUPPLIERS ||--o{ SCHEDULES : "提供船期"
    SUPPLIERS ||--o{ BILLING_RULES : "制定计费规则"
    CHANNELS ||--o{ PRICES : "归类"
    CHANNELS ||--o{ SCHEDULES : "关联"
    DESTINATIONS ||--o{ PRICES : "指向"

    SUPPLIERS {
        string code "供应商编码(唯一)"
        string name "供应商名称"
        string line "经营线路(美/欧/加)"
        string status "状态(正常/冻结/搁置)"
        string inbound "进仓点(原始文本)"
        string price_date "价表日期"
    }

    CHANNELS {
        int id "渠道ID"
        string name "标准渠道名(母集)"
        string alias "渠道别名"
        string supplier "所属供应商"
        string mode "运输模式(卡派/海派/空派)"
    }

    PRICES {
        int id "价格ID"
        string supplier "供应商"
        string channel "渠道"
        string destination "目的地/仓库代码"
        real weight_min "重量下限"
        real weight_max "重量上限"
        real rate "单价(底价)"
        string unit "计费单位(按重/按方)"
        string dd "税费类型(双清包税/不包税)"
        int transit_min "时效下限(天)"
        int transit_max "时效上限(天)"
        string valid_from "生效日期"
        string valid_to "失效日期"
        string inbound "进仓点"
        int active "是否活跃"
    }

    SCHEDULES {
        int id "船期ID"
        string supplier "供应商"
        string channel "渠道"
        string loading_port "装货港"
        string vessel "船名/航次"
        date cutoff "截单日期"
        date sailing "开船日期"
        date arrival "到港日期"
    }

    BILLING_RULES {
        int id "规则ID"
        string supplier "供应商"
        string service_type "服务类型"
        string channel_group "渠道组"
        string category "规则类别"
        real threshold "计费门槛"
        real amount "折扣/附加费金额"
        string formula "计费公式"
        string condition "触发条件"
    }

    DESTINATIONS {
        string code "目的地代码"
        string name "名称"
        string type "类型(FBA/沃尔玛/海外仓)"
        string region "区域"
        string country "国家"
    }
```

## 2. 核心实体与关系说明

| 实体 | 职责 | 关键设计 |
|:--|:--|:--|
| 供应商 | 货源主数据 | 一供应商多渠道、多报价、多船期、多规则 |
| 渠道 | 标准归类（母集） | 把供应商五花八门的渠道名统一归并到标准大类 |
| 价格 | 四维报价 | 供应商 × 渠道 × 仓库 × 重量段，锁定唯一底价 |
| 船期 | 截单/开船/到港 | 支持周模式动态推算，应对供应商只给「每周 X 截 Y 开」 |
| 计费规则 | 附加费/折扣 | 比重优惠、尺寸附加、报关费等逐条核 |
| 目的地 | FBA / 沃尔玛 / 海外仓 | 白名单校验，杜绝非法仓码入库 |

## 3. 关系说明

1. **供应商 → 渠道（1:N）**：一家供应商拥有多个渠道，渠道按母集标准归类。
2. **供应商 / 渠道 → 价格（1:N）**：价格同时关联供应商与渠道，形成「供应商 × 渠道 × 仓库 × 重量段」四维报价。
3. **目的地 → 价格（1:N）**：价格指向具体目的地（FBA 仓库代码）。
4. **供应商 → 船期（1:N）**：船期由供应商提供，关联到具体渠道。
5. **供应商 → 计费规则（1:N）**：计费规则按「供应商 + 服务类型 + 渠道组 + 类别」四维锁定。

## 4. 设计要点

- **三库分离**：生产库（只读报价）/ 测试库（技能产出）/ 档案库（趋势历史），旧数据归档后去除时效与规则字段，仅留趋势用。
- **分线路分表**：美线 / 欧线 / 加拿大线物理隔离，禁止跨线路查询。
- **原始名保真**：渠道原始名与进仓点保留 Excel 原文，报价可溯源到原始价表。
- **底价原则**：报价引擎只读数据库原始底价，禁止任何形式加价——这是「宁可不报价、不可报错价」的数据根基。
