# skinCodeAdmin

皮肤站邀请码管理 + QQ群管理插件。

## 简介

这是一个 AstrBot 插件，用于管理皮肤站邀请码和 QQ 群组白名单。支持邀请码自动分配、用户白名单审核、群组加群自动审批、消息群发等功能。

## 配置

在 AstrBot 插件设置中填写以下配置项：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `api_url` | 皮肤站邀请码 API 地址 | `http://example.com/api.php` |
| `admin_api_url` | 皮肤站管理后台 API 地址（用于获取邀请码） | `http://example.com/api.php` |
| `admin_password` | 皮肤站管理员密码 | `your_admin_password` |

### API 接口说明

#### api_url（邀请码列表接口）

- **请求方式**: `GET`
- **返回示例**:
```json
{
  "free": [
    {"code": "ABC123"},
    {"code": "DEF456"}
  ],
  "used": [
    {"code": "XYZ789", "used_by": "10001"}
  ]
}
```

#### admin_api_url（邀请码分配接口）

- **请求方式**: `POST`
- **请求参数**:
  | 参数 | 说明 |
  |------|------|
  | `action` | 固定值 `admin_direct_assign` |
  | `qq` | 用户 QQ 号 |
  | `admin_password` | 管理员密码（对应配置的 `admin_password`） |

- **返回示例（成功）**:
```json
{
  "success": true,
  "data": {
    "code": "ABC123"
  }
}
```

- **返回示例（失败）**:
```json
{
  "success": false,
  "message": "错误信息"
}
```

## 指令列表

| 指令 | 别名 | 权限要求 | 说明 | 参数 |
|------|------|----------|------|------|
| `/code_init` | - | 管理员 | 重新读取数据文件 | - |
| `/getallcodes` | - | 管理员 | 获取服务端所有邀请码（剩余/已使用数量） | - |
| `/getmecode` | `/获取邀请码` | 无（仅限私聊） | 获取皮肤站邀请码 | - |
| `/pass` | - | 管理员 | 通过用户白名单 | `<QQ号>` |
| `/ban` | - | 管理员 | 封禁用户（并从相关群踢出） | `<QQ号>` |
| `/unban` | - | 管理员 | 解封用户 | `<QQ号>` |
| `/invite` | `/邀请` | 无 | 邀请用户通过白名单（邀请者需先通过白名单） | `<QQ号>` |
| `/sugroup` | - | 管理员 | 设置当前群为用户群（白名单自动审批群） | - |
| `/rugroup` | - | 管理员 | 取消当前群为用户群 | - |
| `/smgroup` | `/设置为消息群` | 无 | 设置当前群为消息群（可接收群发消息） | - |
| `/rmgroup` | `/取消为消息群` | 无 | 取消当前群为消息群 | - |
| `/send` | `/推送` | 管理员或消息推送权限 | 发送消息到所有消息群 | `<消息内容>` |
| `/query` | `/查询` | 无 | 查询用户信息 | `<QQ号>` 或 `<皮肤站UID>` |
| `/setname` | - | 无 | 设置自己的昵称 | `<昵称>` |
| `/setmsgop` | - | 管理员 | 设置用户消息推送权限 | `<QQ号>` |
| `/rmmsgop` | - | 管理员 | 取消用户消息推送权限 | `<QQ号>` |
| `/sync` | - | 管理员 | 同步皮肤站用户信息 | - |
| `/allban` | - | 管理员 | 封禁用户及其所有关联用户 | `<QQ号>` |

## 权限说明

- **管理员**: 需要 AstrBot 管理员权限（`PermissionType.ADMIN`）
- **消息推送权限**: 用户数据中的 `ismsgop` 字段为 `True`，由管理员通过 `/setmsgop` 指令设置
- **无**: 所有用户均可使用（部分指令有特殊限制，如私聊限制）

### 用户数据字段说明

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `id` | string | 用户 QQ 号 | - |
| `name` | string | 用户昵称 | "" |
| `code` | string | 皮肤站邀请码 | "" |
| `skin_uid` | string | 皮肤站 UID | "" |
| `is_pass` | bool | 是否通过白名单 | False |
| `is_banned` | bool | 是否被封禁 | False |
| `ismsgop` | bool | 是否有消息推送权限 | False |
| `superior` | string | 邀请者 QQ 号 | "" |
| `subordinates` | list | 邀请的用户列表 | [] |
