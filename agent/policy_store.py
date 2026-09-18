"""Dependency-free lexical policy search over ingested chunks."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any


_TOKEN_PATTERN = re.compile(r"\b\w+\b", re.UNICODE)


class PolicyStore:
    """Small in-memory store compatible with the policy retriever."""

    def __init__(self) -> None:
        self._documents: list[dict[str, Any]] = []
        self._tokens: list[set[str]] = []

    def add_documents(self, documents: list[Mapping[str, Any]]) -> None:
        """Add searchable policy chunks while preserving their full structure."""

        if not isinstance(documents, list):
            raise TypeError("documents must be a list")

        for document in documents:
            if not isinstance(document, Mapping):
                raise ValueError("each policy document must be a mapping")
            content = document.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("each policy document must contain non-empty content")
            metadata = document.get("metadata", {})
            if not isinstance(metadata, Mapping):
                raise ValueError("policy document metadata must be a mapping")

            stored = dict(document)
            stored["content"] = content
            stored["metadata"] = dict(metadata)
            self._documents.append(stored)
            self._tokens.append(set(_tokenize(content)))

    def similarity_search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Return up to ``k`` matching chunks ranked by lexical relevance."""

        return [document for document, _ in self._ranked(query, k)]

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[dict[str, Any], float]]:
        """Return matching chunks and their deterministic lexical scores."""

        return self._ranked(query, k)

    def _ranked(self, query: str, k: int) -> list[tuple[dict[str, Any], float]]:
        if not isinstance(query, str) or not query.strip() or k < 1:
            return []

        query_text = query.strip().casefold()
        query_tokens = _tokenize(query_text)
        if not query_tokens:
            return []

        document_frequency = {
            token: sum(token in tokens for tokens in self._tokens)
            for token in set(query_tokens)
        }
        ranked: list[tuple[float, str, int, dict[str, Any]]] = []
        for index, (document, tokens) in enumerate(zip(self._documents, self._tokens)):
            score = _score_document(
                query_text,
                query_tokens,
                document,
                tokens,
                document_frequency,
                len(self._documents),
            )
            if score <= 0:
                continue
            chunk_id = str(document.get("chunk_id", ""))
            ranked.append((score, chunk_id, index, _copy_document(document)))

        ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [(document, score) for score, _, _, document in ranked[:k]]


def _score_document(
    query_text: str,
    query_tokens: Sequence[str],
    document: Mapping[str, Any],
    tokens: set[str],
    document_frequency: Mapping[str, int],
    document_count: int,
) -> float:
    content = str(document["content"]).casefold()
    content_tokens = _tokenize(content)
    term_frequency = {token: content_tokens.count(token) for token in set(query_tokens)}
    matched = [token for token in query_tokens if token in tokens]
    if not matched:
        return 0.0

    score = 0.0
    for token in set(matched):
        inverse_frequency = math.log((document_count + 1) / (document_frequency[token] + 1)) + 1
        score += term_frequency[token] * inverse_frequency
    score += len(set(matched)) / len(set(query_tokens))
    if query_text in content:
        score += 1.0
    return score


def _copy_document(document: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(document)
    metadata = copied.get("metadata")
    if isinstance(metadata, Mapping):
        copied["metadata"] = dict(metadata)
    return copied


def _tokenize(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_PATTERN.findall(text)]


__all__ = ["PolicyStore"]