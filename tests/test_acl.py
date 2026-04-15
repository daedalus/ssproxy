"""Tests for ACL functionality."""

import pytest

from src.ssproxy.acl import (
    ACLAction,
    ACLConfig,
    ACLRule,
    ACLRuleType,
    load_acl_from_dict,
    parse_acl_rule,
)


class TestACLRule:
    def test_cidr_match_exact(self):
        rule = ACLRule(ACLAction.ALLOW, ACLRuleType.CIDR, "192.168.1.100/32")
        assert rule.matches("192.168.1.100") is True
        assert rule.matches("192.168.1.101") is False

    def test_cidr_match_network(self):
        rule = ACLRule(ACLAction.ALLOW, ACLRuleType.CIDR, "192.168.1.0/24")
        assert rule.matches("192.168.1.1") is True
        assert rule.matches("192.168.1.255") is True
        assert rule.matches("192.168.2.1") is False

    def test_cidr_match_ipv6(self):
        rule = ACLRule(ACLAction.ALLOW, ACLRuleType.CIDR, "::1/128")
        assert rule.matches("::1") is True
        assert rule.matches("::2") is False

    def test_cidr_invalid_ip(self):
        rule = ACLRule(ACLAction.ALLOW, ACLRuleType.CIDR, "192.168.1.0/24")
        assert rule.matches("invalid") is False

    def test_fqdn_match_exact(self):
        rule = ACLRule(ACLAction.ALLOW, ACLRuleType.FQDN, "example.com")
        assert rule.matches("192.168.1.1", "example.com") is True
        assert rule.matches("192.168.1.1", "example.org") is False

    def test_fqdn_match_wildcard(self):
        rule = ACLRule(ACLAction.ALLOW, ACLRuleType.FQDN, "*.example.com")
        assert rule.matches("192.168.1.1", "api.example.com") is True
        assert rule.matches("192.168.1.1", "www.api.example.com") is True
        assert rule.matches("192.168.1.1", "example.com") is True
        assert rule.matches("192.168.1.1", "notexample.com") is False
        assert rule.matches("192.168.1.1", "evil.com") is False

    def test_fqdn_case_insensitive(self):
        rule = ACLRule(ACLAction.ALLOW, ACLRuleType.FQDN, "EXAMPLE.COM")
        assert rule.matches("192.168.1.1", "example.com") is True

    def test_fqdn_no_target(self):
        rule = ACLRule(ACLAction.ALLOW, ACLRuleType.FQDN, "example.com")
        assert rule.matches("192.168.1.1", None) is False

    def test_empty_rules_skipped(self):
        data = {
            "enabled": True,
            "rules": [
                {"action": "allow", "type": "cidr", "value": ""},
                {"action": "deny", "type": "cidr", "value": "192.168.1.0/24"},
            ],
        }
        acl = load_acl_from_dict(data)
        assert len(acl.rules) == 1
        assert acl.check("192.168.1.1") == ACLAction.DENY


class TestACLConfig:
    def test_disabled_acl_always_allows(self):
        acl = ACLConfig(enabled=False)
        acl.add_rule(ACLAction.DENY, ACLRuleType.CIDR, "10.0.0.0/8")
        assert acl.check("10.1.1.1") == ACLAction.ALLOW

    def test_default_deny(self):
        acl = ACLConfig(enabled=True, default_action=ACLAction.DENY)
        assert acl.check("192.168.1.1") == ACLAction.DENY

    def test_default_allow(self):
        acl = ACLConfig(enabled=True, default_action=ACLAction.ALLOW)
        assert acl.check("192.168.1.1") == ACLAction.ALLOW

    def test_rule_matching(self):
        acl = ACLConfig(enabled=True, default_action=ACLAction.DENY)
        acl.add_rule(ACLAction.ALLOW, ACLRuleType.CIDR, "192.168.1.0/24")
        assert acl.check("192.168.1.100") == ACLAction.ALLOW
        assert acl.check("10.1.1.1") == ACLAction.DENY

    def test_first_rule_wins(self):
        acl = ACLConfig(enabled=True, default_action=ACLAction.DENY)
        acl.add_rule(ACLAction.ALLOW, ACLRuleType.CIDR, "192.168.1.0/24")
        acl.add_rule(ACLAction.DENY, ACLRuleType.CIDR, "192.168.1.100/32")
        assert acl.check("192.168.1.100") == ACLAction.ALLOW
        assert acl.check("192.168.1.50") == ACLAction.ALLOW

    def test_fqdn_rule(self):
        acl = ACLConfig(enabled=True, default_action=ACLAction.DENY)
        acl.add_rule(ACLAction.ALLOW, ACLRuleType.FQDN, "api.example.com")
        assert acl.check("192.168.1.1", "api.example.com") == ACLAction.ALLOW
        assert acl.check("192.168.1.1", "other.com") == ACLAction.DENY


class TestParseACLRule:
    def test_parse_cidr_rule(self):
        rule = parse_acl_rule("allow", "cidr", "192.168.1.0/24")
        assert rule.action == ACLAction.ALLOW
        assert rule.rule_type == ACLRuleType.CIDR
        assert rule.value == "192.168.1.0/24"

    def test_parse_fqdn_rule(self):
        rule = parse_acl_rule("deny", "fqdn", "*.evil.com")
        assert rule.action == ACLAction.DENY
        assert rule.rule_type == ACLRuleType.FQDN
        assert rule.value == "*.evil.com"

    def test_parse_invalid_action(self):
        with pytest.raises(ValueError, match="Invalid ACL action"):
            parse_acl_rule("invalid", "cidr", "192.168.1.0/24")

    def test_parse_invalid_rule_type(self):
        with pytest.raises(ValueError, match="Invalid ACL rule type"):
            parse_acl_rule("allow", "invalid", "test.com")

    def test_parse_invalid_cidr(self):
        with pytest.raises(ValueError, match="Invalid CIDR notation"):
            parse_acl_rule("allow", "cidr", "not-a-cidr")


class TestLoadACLFromDict:
    def test_load_basic_acl(self):
        data = {
            "enabled": True,
            "default_action": "deny",
            "rules": [
                {"action": "allow", "type": "cidr", "value": "192.168.1.0/24"},
                {"action": "deny", "type": "fqdn", "value": "*.evil.com"},
            ],
        }
        acl = load_acl_from_dict(data)

        assert acl.enabled is True
        assert acl.default_action == ACLAction.DENY
        assert len(acl.rules) == 2

    def test_load_acl_with_defaults(self):
        data = {"enabled": False}
        acl = load_acl_from_dict(data)

        assert acl.enabled is False
        assert acl.default_action == ACLAction.DENY
        assert len(acl.rules) == 0

    def test_load_acl_with_alias_fields(self):
        data = {
            "enabled": True,
            "rules": [
                {"action": "allow", "rule_type": "cidr", "pattern": "10.0.0.0/8"},
            ],
        }
        acl = load_acl_from_dict(data)

        assert len(acl.rules) == 1
        assert acl.rules[0].value == "10.0.0.0/8"

    def test_load_acl_invalid_default_action(self):
        data = {"default_action": "invalid"}
        with pytest.raises(ValueError, match="Invalid default_action"):
            load_acl_from_dict(data)


class TestACLConfigSerialization:
    def test_to_dict(self):
        acl = ACLConfig(enabled=True, default_action=ACLAction.DENY)
        acl.add_rule(ACLAction.ALLOW, ACLRuleType.CIDR, "192.168.1.0/24")

        result = acl.to_dict()

        assert result["enabled"] is True
        assert result["default_action"] == "deny"
        assert len(result["rules"]) == 1
        assert result["rules"][0]["action"] == "allow"
        assert result["rules"][0]["type"] == "cidr"
        assert result["rules"][0]["value"] == "192.168.1.0/24"

    def test_rule_to_dict(self):
        rule = ACLRule(ACLAction.DENY, ACLRuleType.FQDN, "*.evil.com")
        result = rule.to_dict()

        assert result["action"] == "deny"
        assert result["type"] == "fqdn"
        assert result["value"] == "*.evil.com"
