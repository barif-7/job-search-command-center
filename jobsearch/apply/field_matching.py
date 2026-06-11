from __future__ import annotations

from typing import Any

DEMOGRAPHIC_HINTS = [
    "age",
    "ethnicity",
    "gender",
    "sex",
    "race",
    "pronoun",
    "disability",
    "veteran",
    "self-identification",
    "demographic",
]


def normalize(text: str | None) -> str:
    return " ".join((text or "").strip().lower().split())


def looks_demographic(text: str) -> bool:
    return any(hint in normalize(text) for hint in DEMOGRAPHIC_HINTS)


def is_hidden_candidate(attrs: dict[str, Any]) -> bool:
    hay = normalize(" ".join(str(v or "") for v in attrs.values()))
    hidden_tokens = [
        "h-captcha",
        "hcaptcha",
        "captcha",
        "recaptcha",
        "survey",
        "ethnicity",
        "gender",
        "veteran",
        "disability",
        "demographic",
        "race",
        "pronouns",
        "age",
    ]
    return any(tok in hay for tok in hidden_tokens)


def field_haystack(attrs: dict[str, Any]) -> str:
    return normalize(
        " ".join(str(attrs.get(k, "")) for k in ["tag", "type", "name", "id", "placeholder", "ariaLabel", "label", "text"])
    )


def score_field(attrs: dict[str, Any], hints: list[str]) -> int:
    hay = field_haystack(attrs)
    return sum(1 for hint in hints if normalize(hint) in hay)


def collect_visible_fields(frame) -> dict[str, list[dict[str, Any]]]:
    field_data: dict[str, list[dict[str, Any]]] = {"inputs": [], "textareas": [], "selects": [], "radios": [], "buttons": []}

    def safe_collect(selector: str, kind: str) -> None:
        try:
            count = frame.locator(selector).count()
        except Exception:
            return
        for i in range(count):
            try:
                el = frame.locator(selector).nth(i)
                if not el.is_visible():
                    continue
                attrs = {
                    "tag": el.evaluate("el => el.tagName"),
                    "type": el.get_attribute("type") or "",
                    "name": el.get_attribute("name") or "",
                    "id": el.get_attribute("id") or "",
                    "placeholder": el.get_attribute("placeholder") or "",
                    "ariaLabel": el.get_attribute("aria-label") or "",
                    "required": bool(el.get_attribute("required")) or bool(el.evaluate("el => el.required || el.hasAttribute('required')")),
                    "label": el.evaluate("el => el.labels && el.labels[0] ? el.labels[0].innerText.trim() : ''"),
                    "text": el.inner_text() if kind == "buttons" else "",
                }
                if kind == "buttons" and attrs["tag"] == "INPUT":
                    attrs["text"] = el.get_attribute("value") or ""
                if kind == "radios" and attrs["type"] not in ("radio", "checkbox"):
                    continue
                if attrs["type"] == "hidden" or is_hidden_candidate(attrs):
                    continue
                field_data[kind].append(attrs)
            except Exception:
                continue

    safe_collect("input", "inputs")
    safe_collect("textarea", "textareas")
    safe_collect("select", "selects")
    safe_collect("input[type='radio'], input[type='checkbox']", "radios")
    safe_collect("button, input[type='submit']", "buttons")
    return field_data


def locate_best_field(frame, hints: list[str], kinds=("inputs", "textareas", "selects")):
    selectors = []
    if "inputs" in kinds:
        selectors.append("input")
    if "textareas" in kinds:
        selectors.append("textarea")
    if "selects" in kinds:
        selectors.append("select")

    best = (0, None, {})
    for selector in selectors:
        try:
            count = frame.locator(selector).count()
        except Exception:
            continue
        for i in range(count):
            try:
                el = frame.locator(selector).nth(i)
                if not el.is_visible() or not el.is_enabled():
                    continue
                attrs = {
                    "tag": el.evaluate("el => el.tagName"),
                    "type": el.get_attribute("type") or "",
                    "name": el.get_attribute("name") or "",
                    "id": el.get_attribute("id") or "",
                    "placeholder": el.get_attribute("placeholder") or "",
                    "ariaLabel": el.get_attribute("aria-label") or "",
                    "label": el.evaluate("el => el.labels && el.labels[0] ? el.labels[0].innerText.trim() : ''"),
                }
                if attrs["type"] == "hidden" or is_hidden_candidate(attrs):
                    continue
                score = score_field(attrs, hints)
                if score > best[0]:
                    best = (score, el, attrs)
            except Exception:
                continue
    return best[1], best[2], best[0]


def fill_text_if_possible(frame, hints: list[str], value: str, kinds=("inputs", "textareas", "selects")):
    if not value:
        return False, {}
    el, attrs, score = locate_best_field(frame, hints, kinds=kinds)
    if not el or score <= 0:
        return False, {}
    try:
        if el.evaluate("el => el.tagName") == "SELECT":
            try:
                el.select_option(label=value)
            except Exception:
                el.select_option(value=value)
        else:
            el.fill(value)
        return True, attrs
    except Exception:
        return False, attrs


def fill_boolean_answers(frame, checkbox_answers: dict[str, Any], radio_answers: dict[str, Any]):
    filled = []
    skipped = []

    for question, answer in (checkbox_answers or {}).items():
        if answer is not True:
            skipped.append({"field": f"checkbox:{question}", "reason": "answer not true"})
            continue
        if looks_demographic(question):
            skipped.append({"field": f"checkbox:{question}", "reason": "demographic question skipped"})
            continue
        ok, attrs = click_choice(frame, question, expected_value=True, selector="input[type='checkbox']")
        if ok:
            filled.append({"field": f"checkbox:{question}", "value": True, "matched": attrs})
        else:
            skipped.append({"field": f"checkbox:{question}", "reason": "no confident visible match"})

    for question, answer in (radio_answers or {}).items():
        if not answer:
            skipped.append({"field": f"radio:{question}", "reason": "empty answer"})
            continue
        if looks_demographic(question):
            skipped.append({"field": f"radio:{question}", "reason": "demographic question skipped"})
            continue
        ok, attrs = click_choice(frame, question, expected_value=str(answer), selector="input[type='radio']")
        if ok:
            filled.append({"field": f"radio:{question}", "value": answer, "matched": attrs})
        else:
            skipped.append({"field": f"radio:{question}", "reason": "no confident visible match"})

    return filled, skipped


def click_choice(frame, question: str, expected_value: str | bool, selector: str):
    q = normalize(question)
    a = normalize(str(expected_value))
    best = None
    best_score = 0
    best_attrs: dict[str, Any] = {}
    try:
        controls = frame.locator(selector)
        count = controls.count()
    except Exception:
        return False, {}

    for i in range(count):
        try:
            el = controls.nth(i)
            if not el.is_visible() or not el.is_enabled():
                continue
            attrs = {
                "type": el.get_attribute("type") or "",
                "name": el.get_attribute("name") or "",
                "id": el.get_attribute("id") or "",
                "label": el.evaluate("el => el.labels && el.labels[0] ? el.labels[0].innerText.trim() : ''"),
                "aria": el.get_attribute("aria-label") or "",
                "value": el.get_attribute("value") or "",
            }
            hay = normalize(" ".join(str(v) for v in attrs.values()))
            score = 0
            if q and q in hay:
                score += 5
            if a and a in hay:
                score += 3
            if normalize(attrs["label"]) in q or q in normalize(attrs["label"]):
                score += 2
            if score > best_score:
                best = el
                best_score = score
                best_attrs = attrs
        except Exception:
            continue

    if best is None or best_score <= 0:
        return False, {}
    try:
        best.check()
        return True, best_attrs
    except Exception:
        return False, best_attrs

