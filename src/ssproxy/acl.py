"""Access Control List (ACL) management for HTTP proxy."""

import ipaddress
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ACLRuleType(Enum):
    CIDR = "cidr"
    FQDN = "fqdn"


class ACLAction(Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class ACLRule:
    action: ACLAction
    rule_type: ACLRuleType
    value: str

    def matches(self, client_ip: str, target_host: str | None = None) -> bool:
        if self.rule_type == ACLRuleType.CIDR:
            return self._matches_cidr(client_ip)
        elif self.rule_type == ACLRuleType.FQDN:
            return self._matches_fqdn(target_host)
        return False

    def _matches_cidr(self, client_ip: str) -> bool:
        try:
            network = ipaddress.ip_network(self.value, strict=False)
            ip = ipaddress.ip_address(client_ip)
            return ip in network
        except ValueError:
            return False

    def _matches_fqdn(self, target_host: str | None) -> bool:
        if target_host is None:
            return False
        return self._hostname_matches(target_host, self.value)

    def _hostname_matches(self, hostname: str, pattern: str) -> bool:
        hostname = hostname.lower()
        pattern = pattern.lower()

        if pattern.startswith("*."):
            base_domain = pattern[2:]
            return hostname == base_domain or hostname.endswith("." + base_domain)

        return hostname == pattern

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "type": self.rule_type.value,
            "value": self.value,
        }


@dataclass
class ACLConfig:
    enabled: bool = False
    default_action: ACLAction = ACLAction.DENY
    rules: list[ACLRule] = field(default_factory=list)

    def add_rule(self, action: ACLAction, rule_type: ACLRuleType, value: str) -> None:
        self.rules.append(ACLRule(action, rule_type, value))

    def check(self, client_ip: str, target_host: str | None = None) -> ACLAction:
        if not self.enabled:
            return ACLAction.ALLOW

        for rule in self.rules:
            if rule.matches(client_ip, target_host):
                return rule.action

        return self.default_action

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "default_action": self.default_action.value,
            "rules": [rule.to_dict() for rule in self.rules],
        }


def parse_acl_rule(action: str, rule_type: str, value: str) -> ACLRule:
    try:
        action_enum = ACLAction(action.lower())
    except ValueError:
        raise ValueError(f"Invalid ACL action: {action}. Must be 'allow' or 'deny'.")

    try:
        rule_type_enum = ACLRuleType(rule_type.lower())
    except ValueError:
        raise ValueError(
            f"Invalid ACL rule type: {rule_type}. Must be 'cidr' or 'fqdn'."
        )

    if rule_type_enum == ACLRuleType.CIDR:
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR notation: {value}. {e}")

    return ACLRule(action_enum, rule_type_enum, value)


def load_acl_from_dict(data: dict[str, Any]) -> ACLConfig:
    acl = ACLConfig(enabled=data.get("enabled", False))

    default_action = data.get("default_action", "deny")
    try:
        acl.default_action = ACLAction(default_action.lower())
    except ValueError:
        raise ValueError(
            f"Invalid default_action: {default_action}. Must be 'allow' or 'deny'."
        )

    for rule_data in data.get("rules", []):
        action = rule_data.get("action", "deny")
        rule_type = rule_data.get("type", rule_data.get("rule_type", "cidr"))
        value = rule_data.get("value", rule_data.get("pattern", ""))

        if not value:
            continue

        acl.rules.append(parse_acl_rule(action, rule_type, value))

    return acl
