"""Retrieve policy chunks from an existing vector store or retriever."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from .state import DocumentMetadata


class RetrievedChunk(TypedDict, total=False):
    """Normalized retrieval result compatible with ``AgentState`` fields."""

    content: str
    metadata: DocumentMetadata
    score: float
    chunk_id: str
    document_name: str


class RetrievalError(RuntimeError):
    """Raised when a configured retrieval backend cannot be queried."""


def retrieve_documents(
    query: str,
    top_k: int = 5,
    vector_store: Any | None = None,
) -> list[RetrievedChunk]:
    """Return the most relevant policy chunks for ``query``.

    ``vector_store`` should be an existing project retriever or vector store.
    Common LangChain-style methods are supported without importing LangChain:
    ``similarity_search_with_score``, ``similarity_search``, ``invoke``, and
    ``get_relevant_documents``. A missing backend is reported explicitly
    because this repository does not yet define one.
    """

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be greater than zero")
    if vector_store is None:
        raise RetrievalError("no vector store or retriever was configured")

    try:
        raw_results = _search(vector_store, normalized_query, top_k)
    except RetrievalError:
        raise
    except Exception as exc:
        raise RetrievalError("policy document retrieval failed") from exc

    if raw_results is None:
        return []
    if isinstance(raw_results, (str, bytes)):
        raw_results = [raw_results]

    try:
        return [
            normalized
            for item in raw_results
            if (normalized := _normalize_result(item)) is not None
        ]
    except (TypeError, ValueError) as exc:
        raise RetrievalError("retriever returned malformed results") from exc


def _search(vector_store: Any, query: str, top_k: int) -> Any:
    """Call the first supported search interface on ``vector_store``."""

    if callable(getattr(vector_store, "similarity_search_with_score", None)):
        return vector_store.similarity_search_with_score(query, k=top_k)
    if callable(getattr(vector_store, "similarity_search", None)):
        return vector_store.similarity_search(query, k=top_k)
    if callable(getattr(vector_store, "get_relevant_documents", None)):
        return vector_store.get_relevant_documents(query)
    if callable(getattr(vector_store, "invoke", None)):
        return vector_store.invoke(query)
    raise RetrievalError("configured retriever has no supported search method")


def _normalize_result(result: Any) -> RetrievedChunk | None:
    """Convert a backend-specific result into a state-friendly chunk."""

    score: float | None = None
    document = result
    if _is_scored_pair(result):
        document, score = result[0], _as_float(result[1])

    if isinstance(document, Mapping):
        content = document.get("content", document.get("text", document.get("page_content")))
        metadata_value = document.get("metadata", {})
        chunk_id = document.get("chunk_id") or document.get("id")
    else:
        content = getattr(document, "page_content", None)
        metadata_value = getattr(document, "metadata", {})
        chunk_id = getattr(document, "chunk_id", None) or getattr(document, "id", None)

    if content is None:
        if isinstance(document, str):
            content = document
        else:
            return None

    if not isinstance(content, str) or not content.strip():
        return None

    metadata = _normalize_metadata(metadata_value)
    normalized: RetrievedChunk = {
        "content": content,
        "metadata": metadata,
    }
    if score is not None:
        normalized["score"] = score
    if chunk_id is not None:
        normalized["chunk_id"] = str(chunk_id)

    document_name = metadata.get("title") or metadata.get("source")
    if document_name:
        normalized["document_name"] = document_name
    return normalized


def _is_scored_pair(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_metadata(value: Any) -> DocumentMetadata:
    if not isinstance(value, Mapping):
        return {}

    metadata: DocumentMetadata = {}
    aliases = {
        "document_id": ("document_id", "doc_id"),
        "title": ("title", "document_name", "name"),
        "source": ("source", "source_file", "file_name"),
        "page": ("page", "page_number"),
        "section": ("section", "section_name"),
        "uri": ("uri", "url"),
    }
    for target, keys in aliases.items():
        for key in keys:
            if value.get(key) is not None:
                metadata[target] = value[key]
                break
    return metadata


__all__ = ["RetrievedChunk", "RetrievalError", "retrieve_documents"]