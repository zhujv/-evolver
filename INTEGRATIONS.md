# 办公集成配置

Evolver 现已提供以下办公平台接入能力：

- `Gmail`
- `Google Calendar`
- `Outlook / Microsoft Graph`
- `飞书`
- `钉钉`

## 配置位置

默认配置文件位于：

```text
~/.evolver/config.json
```

## 示例配置

```json
{
  "integrations": {
    "gmail": {
      "enabled": true,
      "client_id": "your-google-client-id",
      "client_secret": "your-google-client-secret",
      "refresh_token": "your-google-refresh-token",
      "from_email": "you@example.com",
      "require_send_confirmation": true
    },
    "google_calendar": {
      "enabled": true,
      "client_id": "your-google-client-id",
      "client_secret": "your-google-client-secret",
      "refresh_token": "your-google-refresh-token",
      "calendar_id": "primary",
      "require_create_confirmation": true
    },
    "outlook": {
      "enabled": true,
      "tenant_id": "common",
      "client_id": "your-microsoft-client-id",
      "client_secret": "your-microsoft-client-secret",
      "refresh_token": "your-microsoft-refresh-token",
      "scope": "offline_access Mail.ReadWrite Mail.Send Calendars.ReadWrite",
      "timezone": "UTC",
      "require_send_confirmation": true,
      "require_create_confirmation": true
    },
    "feishu": {
      "enabled": true,
      "app_id": "cli_xxx",
      "app_secret": "xxx",
      "receive_id_type": "open_id"
    },
    "dingtalk": {
      "enabled": true,
      "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
      "secret": "SECxxx"
    }
  }
}
```

## 已接入工具

- `gmail_draft`
- `gmail_send`
- `gmail_search`
- `calendar_create_event`
- `calendar_list_events`
- `outlook_mail_draft`
- `outlook_mail_send`
- `outlook_mail_search`
- `outlook_calendar_create`
- `outlook_calendar_list`
- `feishu_message_send`
- `dingtalk_message_send`

## 说明

- `Gmail` 与 `Google Calendar` 已按 refresh token 模式走真实 API 调用。
- `Outlook` 通过 `Microsoft Graph` 调用邮件与日历接口。
- `飞书` 当前接入租户访问令牌与消息发送接口。
- `钉钉` 当前采用机器人 webhook 发送消息，支持签名 secret。
- 发送邮件、创建日程这类高风险动作默认要求显式确认。
