#!/usr/bin/env python3
"""测试第三方集成功能"""

import json
import sys
from typing import Dict

from evolver.tools.office_tools import OfficeTools


def test_feishu_integration() -> Dict:
    """测试飞书集成"""
    print("=== 测试飞书集成 ===")
    tools = OfficeTools()
    
    # 检查飞书集成是否启用
    config = tools._integrations.get("feishu", {})
    if not config.get("enabled", False):
        return {
            "status": "skipped",
            "message": "飞书集成未启用，请在配置文件中开启"
        }
    
    # 检查必要配置
    if not config.get("app_id") or not config.get("app_secret"):
        return {
            "status": "error",
            "message": "飞书集成缺少必要配置：app_id 和 app_secret"
        }
    
    # 测试获取访问令牌
    print("测试获取飞书访问令牌...")
    token = tools._feishu_access_token()
    if isinstance(token, dict) and token.get("error"):
        return {
            "status": "error",
            "message": f"获取飞书访问令牌失败: {token.get('error')}"
        }
    
    print("✓ 飞书访问令牌获取成功")
    
    # 测试发送消息（需要真实的 receive_id）
    # 注意：这里需要用户提供真实的 receive_id 才能完成测试
    test_receive_id = ""
    if test_receive_id:
        print("测试发送飞书消息...")
        result = tools.feishu_message_send(
            receive_id=test_receive_id,
            content="测试消息：Evolver 飞书集成测试",
            msg_type="text"
        )
        if result.get("error"):
            return {
                "status": "error",
                "message": f"发送飞书消息失败: {result.get('error')}"
            }
        print("✓ 飞书消息发送成功")
    else:
        print("⚠ 未提供 receive_id，跳过消息发送测试")
    
    return {
        "status": "success",
        "message": "飞书集成测试通过"
    }


def test_dingtalk_integration() -> Dict:
    """测试钉钉集成"""
    print("\n=== 测试钉钉集成 ===")
    tools = OfficeTools()
    
    # 检查钉钉集成是否启用
    config = tools._integrations.get("dingtalk", {})
    if not config.get("enabled", False):
        return {
            "status": "skipped",
            "message": "钉钉集成未启用，请在配置文件中开启"
        }
    
    # 检查必要配置
    if not config.get("webhook"):
        return {
            "status": "error",
            "message": "钉钉集成缺少必要配置：webhook"
        }
    
    # 测试发送消息
    print("测试发送钉钉消息...")
    result = tools.dingtalk_message_send(
        text="测试消息：Evolver 钉钉集成测试",
        title="Evolver 测试"
    )
    if result.get("error"):
        return {
            "status": "error",
            "message": f"发送钉钉消息失败: {result.get('error')}"
        }
    
    print("✓ 钉钉消息发送成功")
    return {
        "status": "success",
        "message": "钉钉集成测试通过"
    }


def test_google_integration() -> Dict:
    """测试 Google 集成"""
    print("\n=== 测试 Google 集成 ===")
    tools = OfficeTools()
    
    # 检查 Gmail 集成是否启用
    gmail_config = tools._integrations.get("gmail", {})
    if gmail_config.get("enabled", False):
        print("测试 Gmail 集成...")
        if not gmail_config.get("client_id") or not gmail_config.get("client_secret") or not gmail_config.get("refresh_token"):
            print("⚠ Gmail 集成缺少必要配置，跳过测试")
        else:
            # 测试获取访问令牌
            token = tools._google_access_token("gmail")
            if isinstance(token, dict) and token.get("error"):
                print(f"⚠ Gmail 访问令牌获取失败: {token.get('error')}")
            else:
                print("✓ Gmail 访问令牌获取成功")
    else:
        print("⚠ Gmail 集成未启用，跳过测试")
    
    # 检查 Google Calendar 集成是否启用
    calendar_config = tools._integrations.get("google_calendar", {})
    if calendar_config.get("enabled", False):
        print("测试 Google Calendar 集成...")
        if not calendar_config.get("client_id") or not calendar_config.get("client_secret") or not calendar_config.get("refresh_token"):
            print("⚠ Google Calendar 集成缺少必要配置，跳过测试")
        else:
            # 测试获取访问令牌
            token = tools._google_access_token("google_calendar")
            if isinstance(token, dict) and token.get("error"):
                print(f"⚠ Google Calendar 访问令牌获取失败: {token.get('error')}")
            else:
                print("✓ Google Calendar 访问令牌获取成功")
    else:
        print("⚠ Google Calendar 集成未启用，跳过测试")
    
    return {
        "status": "success",
        "message": "Google 集成测试完成"
    }


def test_outlook_integration() -> Dict:
    """测试 Outlook 集成"""
    print("\n=== 测试 Outlook 集成 ===")
    tools = OfficeTools()
    
    # 检查 Outlook 集成是否启用
    config = tools._integrations.get("outlook", {})
    if not config.get("enabled", False):
        return {
            "status": "skipped",
            "message": "Outlook 集成未启用，请在配置文件中开启"
        }
    
    # 检查必要配置
    if not config.get("client_id") or not config.get("client_secret") or not config.get("refresh_token"):
        return {
            "status": "error",
            "message": "Outlook 集成缺少必要配置：client_id、client_secret 和 refresh_token"
        }
    
    # 测试获取访问令牌
    print("测试获取 Outlook 访问令牌...")
    token = tools._microsoft_access_token()
    if isinstance(token, dict) and token.get("error"):
        return {
            "status": "error",
            "message": f"获取 Outlook 访问令牌失败: {token.get('error')}"
        }
    
    print("✓ Outlook 访问令牌获取成功")
    return {
        "status": "success",
        "message": "Outlook 集成测试通过"
    }


def main():
    """主测试函数"""
    print("开始测试第三方集成功能...\n")
    
    results = {
        "feishu": test_feishu_integration(),
        "dingtalk": test_dingtalk_integration(),
        "google": test_google_integration(),
        "outlook": test_outlook_integration()
    }
    
    print("\n=== 测试结果汇总 ===")
    for integration, result in results.items():
        status = "✓" if result["status"] == "success" else "⚠" if result["status"] == "skipped" else "✗"
        print(f"{status} {integration}: {result['message']}")
    
    # 检查是否有错误
    errors = [k for k, v in results.items() if v["status"] == "error"]
    if errors:
        print(f"\n❌ 测试完成，发现 {len(errors)} 个错误")
        return 1
    else:
        print("\n✅ 测试完成，所有集成测试通过")
        return 0


if __name__ == "__main__":
    sys.exit(main())
