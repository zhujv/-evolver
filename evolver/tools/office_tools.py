"""OfficeTools - 第三方办公集成工具（Google / Outlook / 飞书 / 钉钉）"""

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from typing import Dict, List, Optional

from ..config.loader import ConfigLoader


class OfficeTools:
    """办公集成工具。Google 为真实 API 调用，其余平台提供可落地接入链。"""

    def __init__(self):
        self._config = ConfigLoader().load()
        self._integrations = self._config.get("integrations", {})

    def gmail_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = "",
        bcc: Optional[str] = "",
    ) -> Dict:
        if not self._is_integration_enabled("gmail"):
            return {"error": "Gmail 集成未启用，请在配置中开启 integrations.gmail.enabled"}
        if not to or not subject or not body:
            return {"error": "参数缺失: to/subject/body 必填"}
        raw = self._build_email_raw("gmail", to, subject, body, cc=cc, bcc=bcc)
        return self._google_api_request(
            "gmail",
            "POST",
            "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
            payload={"message": {"raw": raw}},
        )

    def gmail_send(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = "",
        bcc: Optional[str] = "",
        confirm: bool = False,
    ) -> Dict:
        if not self._is_integration_enabled("gmail"):
            return {"error": "Gmail 集成未启用，请在配置中开启 integrations.gmail.enabled"}
        if not to or not subject or not body:
            return {"error": "参数缺失: to/subject/body 必填"}
        gmail_cfg = self._integrations.get("gmail", {})
        if gmail_cfg.get("require_send_confirmation", True) and not confirm:
            return {"error": "发送邮件属于高风险动作，请显式传入 confirm=true 后重试"}
        raw = self._build_email_raw("gmail", to, subject, body, cc=cc, bcc=bcc)
        return self._google_api_request(
            "gmail",
            "POST",
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            payload={"raw": raw},
        )

    def gmail_search(self, query: str, max_results: int = 10) -> Dict:
        if not self._is_integration_enabled("gmail"):
            return {"error": "Gmail 集成未启用，请在配置中开启 integrations.gmail.enabled"}
        if not query:
            return {"error": "query 不能为空"}
        safe_max = max(1, min(int(max_results or 10), 50))
        params = urllib.parse.urlencode({"q": query, "maxResults": safe_max})
        return self._google_api_request(
            "gmail",
            "GET",
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages?{params}",
        )

    def calendar_create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = "",
        attendees: Optional[str] = "",
        confirm: bool = False,
    ) -> Dict:
        if not self._is_integration_enabled("google_calendar"):
            return {"error": "Google Calendar 集成未启用，请在配置中开启 integrations.google_calendar.enabled"}
        if not title or not start_time or not end_time:
            return {"error": "参数缺失: title/start_time/end_time 必填"}
        gcal_cfg = self._integrations.get("google_calendar", {})
        if gcal_cfg.get("require_create_confirmation", True) and not confirm:
            return {"error": "创建日程属于高风险动作，请显式传入 confirm=true 后重试"}
        calendar_id = urllib.parse.quote(gcal_cfg.get("calendar_id", "primary"), safe="")
        attendee_list = [{"email": item} for item in self._split_csv(attendees)]
        payload = {
            "summary": title,
            "description": description or "",
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
        }
        if attendee_list:
            payload["attendees"] = attendee_list
        return self._google_api_request(
            "google_calendar",
            "POST",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            payload=payload,
        )

    def calendar_list_events(
        self,
        start_time: Optional[str] = "",
        end_time: Optional[str] = "",
        max_results: int = 10,
    ) -> Dict:
        if not self._is_integration_enabled("google_calendar"):
            return {"error": "Google Calendar 集成未启用，请在配置中开启 integrations.google_calendar.enabled"}
        gcal_cfg = self._integrations.get("google_calendar", {})
        calendar_id = urllib.parse.quote(gcal_cfg.get("calendar_id", "primary"), safe="")
        safe_max = max(1, min(int(max_results or 10), 50))
        query = {
            "maxResults": safe_max,
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        if start_time:
            query["timeMin"] = start_time
        if end_time:
            query["timeMax"] = end_time
        return self._google_api_request(
            "google_calendar",
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events?{urllib.parse.urlencode(query)}",
        )

    def outlook_mail_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
    ) -> Dict:
        return self._outlook_mail_action(
            endpoint="/me/messages",
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
        )

    def outlook_mail_send(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        confirm: bool = False,
    ) -> Dict:
        cfg = self._integrations.get("outlook", {})
        if cfg.get("require_send_confirmation", True) and not confirm:
            return {"error": "发送 Outlook 邮件属于高风险动作，请显式传入 confirm=true 后重试"}
        return self._outlook_mail_action(
            endpoint="/me/sendMail",
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            wrap_message=True,
        )

    def outlook_mail_search(self, query: str, max_results: int = 10) -> Dict:
        if not self._is_integration_enabled("outlook"):
            return {"error": "Outlook 集成未启用，请在配置中开启 integrations.outlook.enabled"}
        if not query:
            return {"error": "query 不能为空"}
        safe_max = max(1, min(int(max_results or 10), 50))
        url = (
            "https://graph.microsoft.com/v1.0/me/messages"
            f"?$search={urllib.parse.quote(chr(34) + query + chr(34), safe='')}&$top={safe_max}"
        )
        return self._microsoft_api_request("GET", url, extra_headers={"ConsistencyLevel": "eventual"})

    def outlook_calendar_create(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        attendees: str = "",
        confirm: bool = False,
    ) -> Dict:
        if not self._is_integration_enabled("outlook"):
            return {"error": "Outlook 集成未启用，请在配置中开启 integrations.outlook.enabled"}
        cfg = self._integrations.get("outlook", {})
        if cfg.get("require_create_confirmation", True) and not confirm:
            return {"error": "创建 Outlook 日程属于高风险动作，请显式传入 confirm=true 后重试"}
        payload = {
            "subject": title,
            "body": {"contentType": "Text", "content": description or ""},
            "start": {"dateTime": start_time, "timeZone": cfg.get("timezone", "UTC")},
            "end": {"dateTime": end_time, "timeZone": cfg.get("timezone", "UTC")},
            "attendees": [
                {"emailAddress": {"address": item}, "type": "required"}
                for item in self._split_csv(attendees)
            ],
        }
        return self._microsoft_api_request("POST", "https://graph.microsoft.com/v1.0/me/events", payload=payload)

    def outlook_calendar_list(
        self,
        start_time: str = "",
        end_time: str = "",
        max_results: int = 10,
    ) -> Dict:
        if not self._is_integration_enabled("outlook"):
            return {"error": "Outlook 集成未启用，请在配置中开启 integrations.outlook.enabled"}
        safe_max = max(1, min(int(max_results or 10), 50))
        params = {"$top": safe_max, "$orderby": "start/dateTime"}
        if start_time and end_time:
            params["startDateTime"] = start_time
            params["endDateTime"] = end_time
            url = "https://graph.microsoft.com/v1.0/me/calendarView?" + urllib.parse.urlencode(params)
        else:
            url = "https://graph.microsoft.com/v1.0/me/events?" + urllib.parse.urlencode(params)
        return self._microsoft_api_request("GET", url)

    def feishu_message_send(self, receive_id: str, content: str, msg_type: str = "text") -> Dict:
        if not self._is_integration_enabled("feishu"):
            return {"error": "飞书集成未启用，请在配置中开启 integrations.feishu.enabled"}
        if not receive_id or not content:
            return {"error": "参数缺失: receive_id/content 必填"}
        cfg = self._integrations.get("feishu", {})
        receive_id_type = cfg.get("receive_id_type", "open_id")
        token = self._feishu_access_token()
        if isinstance(token, dict) and token.get("error"):
            return token
        payload = {"receive_id": receive_id, "msg_type": msg_type, "content": json.dumps({"text": content})}
        return self._http_json(
            "POST",
            f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={urllib.parse.quote(receive_id_type)}",
            headers={"Authorization": f"Bearer {token}"},
            payload=payload,
        )

    def dingtalk_message_send(self, text: str, title: str = "") -> Dict:
        if not self._is_integration_enabled("dingtalk"):
            return {"error": "钉钉集成未启用，请在配置中开启 integrations.dingtalk.enabled"}
        if not text:
            return {"error": "text 不能为空"}
        cfg = self._integrations.get("dingtalk", {})
        webhook = (cfg.get("webhook") or "").strip()
        if not webhook:
            return {"error": "缺少钉钉 webhook 配置"}
        if cfg.get("secret"):
            webhook = self._signed_dingtalk_webhook(webhook, cfg["secret"])
        payload = {
            "msgtype": "markdown" if title else "text",
            "markdown": {"title": title or "Evolver", "text": text},
            "text": {"content": text},
        }
        return self._http_json("POST", webhook, payload=payload)

    def _outlook_mail_action(
        self,
        endpoint: str,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        wrap_message: bool = False,
    ) -> Dict:
        if not self._is_integration_enabled("outlook"):
            return {"error": "Outlook 集成未启用，请在配置中开启 integrations.outlook.enabled"}
        if not to or not subject or not body:
            return {"error": "参数缺失: to/subject/body 必填"}
        message = {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": self._graph_recipients(to),
            "ccRecipients": self._graph_recipients(cc),
            "bccRecipients": self._graph_recipients(bcc),
        }
        payload = {"message": message, "saveToSentItems": True} if wrap_message else message
        return self._microsoft_api_request("POST", f"https://graph.microsoft.com/v1.0{endpoint}", payload=payload)

    def _google_api_request(self, integration_name: str, method: str, url: str, payload: Optional[Dict] = None) -> Dict:
        token = self._google_access_token(integration_name)
        if isinstance(token, dict) and token.get("error"):
            return token
        return self._http_json(method, url, headers={"Authorization": f"Bearer {token}"}, payload=payload)

    def _microsoft_api_request(
        self,
        method: str,
        url: str,
        payload: Optional[Dict] = None,
        extra_headers: Optional[Dict] = None,
    ) -> Dict:
        token = self._microsoft_access_token()
        if isinstance(token, dict) and token.get("error"):
            return token
        headers = {"Authorization": f"Bearer {token}"}
        if extra_headers:
            headers.update(extra_headers)
        return self._http_json(method, url, headers=headers, payload=payload)

    def _google_access_token(self, integration_name: str):
        cfg = self._integrations.get(integration_name, {})
        if not cfg.get("client_id") or not cfg.get("client_secret") or not cfg.get("refresh_token"):
            return {"error": f"{integration_name} 缺少 client_id/client_secret/refresh_token 配置"}
        return self._oauth_refresh(
            "https://oauth2.googleapis.com/token",
            {
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "refresh_token": cfg["refresh_token"],
                "grant_type": "refresh_token",
            },
        )

    def _microsoft_access_token(self):
        cfg = self._integrations.get("outlook", {})
        tenant = cfg.get("tenant_id", "common")
        if not cfg.get("client_id") or not cfg.get("client_secret") or not cfg.get("refresh_token"):
            return {"error": "outlook 缺少 client_id/client_secret/refresh_token 配置"}
        return self._oauth_refresh(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            {
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "refresh_token": cfg["refresh_token"],
                "grant_type": "refresh_token",
                "scope": cfg.get("scope", "offline_access Mail.ReadWrite Mail.Send Calendars.ReadWrite"),
            },
        )

    def _feishu_access_token(self):
        cfg = self._integrations.get("feishu", {})
        if not cfg.get("app_id") or not cfg.get("app_secret"):
            return {"error": "feishu 缺少 app_id/app_secret 配置"}
        response = self._http_json(
            "POST",
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            payload={"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]},
        )
        if response.get("error"):
            return response
        token = response.get("tenant_access_token")
        if not token:
            return {"error": f"飞书 access token 获取失败: {response}"}
        return token

    def _oauth_refresh(self, token_url: str, form: Dict[str, str]):
        response = self._http_form(token_url, form)
        if response.get("error"):
            return response
        access_token = response.get("access_token")
        if not access_token:
            return {"error": f"OAuth 刷新失败: {response}"}
        return access_token

    def _http_form(self, url: str, form: Dict[str, str]) -> Dict:
        data = urllib.parse.urlencode(form).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        return self._urlopen_json(req)

    def _http_json(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        payload: Optional[Dict] = None,
    ) -> Dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        merged_headers = {"Content-Type": "application/json"}
        if headers:
            merged_headers.update(headers)
        req = urllib.request.Request(url, data=body, headers=merged_headers, method=method.upper())
        return self._urlopen_json(req)

    def _urlopen_json(self, request: urllib.request.Request) -> Dict:
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw else {"success": True, "status_code": resp.status}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(detail) if detail else {}
            except json.JSONDecodeError:
                parsed = {"raw": detail}
            return {"error": f"HTTP {exc.code}", "details": parsed}
        except Exception as exc:
            return {"error": str(exc)}

    def _build_email_raw(self, integration_name: str, to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
        cfg = self._integrations.get(integration_name, {})
        msg = EmailMessage()
        sender = cfg.get("from_email") or "me"
        msg["From"] = sender
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        msg["Subject"] = subject
        msg.set_content(body)
        return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    def _graph_recipients(self, addresses: str) -> List[Dict]:
        return [{"emailAddress": {"address": addr}} for addr in self._split_csv(addresses)]

    def _split_csv(self, value: Optional[str]) -> List[str]:
        return [item.strip() for item in (value or "").split(",") if item.strip()]

    def _signed_dingtalk_webhook(self, webhook: str, secret: str) -> str:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
        sign = urllib.parse.quote_plus(
            base64.b64encode(hmac.new(secret_enc, string_to_sign, digestmod=hashlib.sha256).digest())
        )
        delimiter = "&" if "?" in webhook else "?"
        return f"{webhook}{delimiter}timestamp={timestamp}&sign={sign}"

    def _is_integration_enabled(self, name: str) -> bool:
        enabled = bool(self._integrations.get(name, {}).get("enabled", False))
        return enabled
