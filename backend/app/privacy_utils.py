from __future__ import annotations

import re
from typing import Optional


def mask_value(value: Optional[str], keep_start: int = 2, keep_end: int = 2) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if len(text) <= keep_start + keep_end:
        return "*" * len(text)
    return f"{text[:keep_start]}{'*' * (len(text) - keep_start - keep_end)}{text[-keep_end:]}"


def mask_cpf(value: Optional[str]) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"{digits[:3]}.***.***-{digits[-2:]}"


def mask_email(value: Optional[str]) -> str:
    if value is None:
        return ""
    email = str(value).strip()
    if not email or "@" not in email:
        return mask_value(email, keep_start=2, keep_end=2) if email else ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{'*' * len(local)}@{domain}"
    return f"{local[:2]}{'*' * max(len(local) - 2, 1)}@{domain}"


def mask_name(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    parts = text.split()
    if len(parts) <= 1:
        return mask_value(text, keep_start=1, keep_end=1)
    masked = [parts[0]]
    for part in parts[1:]:
        if len(part) <= 2:
            masked.append(part)
        else:
            masked.append(f"{part[:1]}{'*' * max(len(part) - 1, 1)}")
    return " ".join(masked)


def mask_phone(value: Optional[str]) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"({digits[:2]}) *****-{digits[-2:]}"


def redact_text_for_log(text: Optional[str]) -> str:
    if text is None:
        return ""
    value = str(text)

    value = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", mask_cpf, value)
    value = re.sub(r"\b\d{11}\b", lambda m: mask_cpf(m.group(0)), value)
    value = re.sub(r"(?i)\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", lambda m: mask_email(m.group(0)), value)
    value = re.sub(r"\(\d{2}\)\s*\d{5}-\d{4}|\d{2}\s*\d{9,10}", lambda m: mask_phone(m.group(0)), value)
    return value
