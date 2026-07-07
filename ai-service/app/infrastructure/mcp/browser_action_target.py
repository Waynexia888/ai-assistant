import re
from dataclasses import dataclass
from typing import Any

from app.domain.models.browser import BrowserElement


REF_PATTERN = re.compile(r"^ref=(?P<ref>.+)$")
QUOTED_VALUE_PATTERN = re.compile(r"['\"](?P<value>[^'\"]{2,})['\"]")
ROLE_WORDS = {"button", "link", "textbox", "checkbox", "radio", "menuitem", "tab"}


@dataclass(frozen=True)
class BrowserActionTargetMatch:
    element: BrowserElement
    score: int
    query: str

    @property
    def ref(self) -> str | None:
        selector = self.element.selector or ""
        match = REF_PATTERN.match(selector)
        return match.group("ref") if match else None

    @property
    def label(self) -> str:
        return (
            self.element.name
            or self.element.text
            or self.element.selector
            or self.element.role
            or self.query
        )


class BrowserActionTargetResolver:
    def resolve(
        self,
        *,
        arguments: dict[str, Any],
        elements: list[BrowserElement],
        include_text_argument: bool = True,
    ) -> BrowserActionTargetMatch | None:
        explicit_ref = self._explicit_ref(arguments)
        if explicit_ref:
            return self._match_by_ref(explicit_ref, elements)

        queries = self._target_queries(
            arguments,
            include_text_argument=include_text_argument,
        )
        role_hint = self._role_hint(arguments, queries)
        matches = [
            match
            for query in queries
            for match in self._matches_for_query(query, elements, role_hint)
            if match.ref
        ]
        if not matches:
            return None

        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[0]

    def resolved_arguments(
        self,
        *,
        arguments: dict[str, Any],
        match: BrowserActionTargetMatch,
    ) -> dict[str, Any]:
        resolved = dict(arguments)
        resolved["element"] = match.label
        resolved["ref"] = match.ref
        resolved["target_resolution"] = {
            "query": match.query,
            "role": match.element.role,
            "name": match.element.name,
            "text": match.element.text,
            "selector": match.element.selector,
            "score": match.score,
        }
        return resolved

    def _explicit_ref(self, arguments: dict[str, Any]) -> str | None:
        value = arguments.get("ref")
        if isinstance(value, str) and value.strip():
            return value.strip()

        for key in ("selector", "element", "target"):
            value = arguments.get(key)
            if not isinstance(value, str):
                continue
            match = REF_PATTERN.match(value.strip())
            if match:
                return match.group("ref")
        return None

    def _match_by_ref(
        self,
        ref: str,
        elements: list[BrowserElement],
    ) -> BrowserActionTargetMatch | None:
        target_selector = f"ref={ref}"
        for element in elements:
            if element.selector == target_selector:
                return BrowserActionTargetMatch(element=element, score=1000, query=target_selector)
        return None

    def _target_queries(
        self,
        arguments: dict[str, Any],
        *,
        include_text_argument: bool,
    ) -> list[str]:
        values: list[str] = []
        keys = ["element", "target", "name", "label", "selector"]
        if include_text_argument:
            keys.append("text")
        for key in keys:
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                values.append(value.strip())

        selector = arguments.get("selector")
        if isinstance(selector, str):
            values.extend(match.group("value") for match in QUOTED_VALUE_PATTERN.finditer(selector))
            values.extend(self._selector_tokens(selector))

        element = arguments.get("element")
        if isinstance(element, str):
            values.extend(match.group("value") for match in QUOTED_VALUE_PATTERN.finditer(element))

        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = self._normalize(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(value)
        return deduped

    def _selector_tokens(self, selector: str) -> list[str]:
        tokens = re.split(r"[^A-Za-z0-9]+", selector)
        return [token for token in tokens if len(token) >= 3 and token.lower() not in ROLE_WORDS]

    def _role_hint(
        self,
        arguments: dict[str, Any],
        queries: list[str],
    ) -> str | None:
        role = arguments.get("role")
        if isinstance(role, str) and role.strip():
            return role.strip().lower()

        joined = " ".join(queries).lower()
        for role_name in ROLE_WORDS:
            if role_name in joined:
                return role_name
        return None

    def _matches_for_query(
        self,
        query: str,
        elements: list[BrowserElement],
        role_hint: str | None,
    ) -> list[BrowserActionTargetMatch]:
        normalized_query = self._normalize(query)
        if not normalized_query:
            return []

        matches: list[BrowserActionTargetMatch] = []
        for element in elements:
            if element.visible is False:
                continue
            score = self._score(element, normalized_query, role_hint)
            if score > 0:
                matches.append(
                    BrowserActionTargetMatch(
                        element=element,
                        score=score,
                        query=query,
                    )
                )
        return matches

    def _score(
        self,
        element: BrowserElement,
        normalized_query: str,
        role_hint: str | None,
    ) -> int:
        role = (element.role or "").lower()
        labels = [element.name, element.text, element.selector]
        normalized_labels = [self._normalize(label) for label in labels if label]
        if not normalized_labels:
            return 0

        score = 0
        compact_query = normalized_query.replace(" ", "")
        for label in normalized_labels:
            compact_label = label.replace(" ", "")
            if label == normalized_query:
                score = max(score, 100)
            elif compact_label and compact_label == compact_query:
                score = max(score, 95)
            elif normalized_query in label or label in normalized_query:
                score = max(score, 70)
            elif compact_query and (compact_query in compact_label or compact_label in compact_query):
                score = max(score, 65)

        if score == 0:
            query_tokens = set(self._tokens(normalized_query))
            for label in normalized_labels:
                label_tokens = set(self._tokens(label))
                if query_tokens and query_tokens <= label_tokens:
                    score = max(score, 55)
                elif query_tokens and query_tokens & label_tokens:
                    score = max(score, 25)

        if score == 0:
            return 0
        if role_hint and role == role_hint:
            score += 20
        if role in {"button", "link"}:
            score += 5
        return score

    def _tokens(self, normalized: str) -> list[str]:
        return [token for token in normalized.split(" ") if token]

    def _normalize(self, value: str | None) -> str:
        if not value:
            return ""
        lowered = value.lower().strip()
        lowered = re.sub(r"&[a-z]+;", " ", lowered)
        lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()
