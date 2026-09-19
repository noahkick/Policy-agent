"""Load policy text files and convert them into traceable search chunks."""

from __future__ import annotations

import re
from pathlib import Path
from collections.abc import Mapping
from typing import Any, TypedDict


class PolicyChunk(TypedDict, total=False):
    """A searchable policy chunk compatible with ``agent.retriever``."""

    content: str
    metadata: dict[str, Any]
    chunk_id: str
    document_name: str


class IngestionError(ValueError):
    """Raised when a policy path or document cannot be ingested."""


SUPPORTED_SUFFIXES = frozenset({".txt", ".md", ".markdown"})
_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_POLICY_METADATA_PATTERN = re.compile(
    r"^\s*\*\*(Policy ID|Version|Effective date|Scope|Region|Department|Vendor):\*\*\s*(.*?)\s*$",
    re.IGNORECASE,
)


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 100,
    *,
    source: str | None = None,
    document_name: str | None = None,
    policy_metadata: Mapping[str, Any] | None = None,
) -> list[PolicyChunk]:
    """Split text at paragraph boundaries while retaining section metadata."""

    if chunk_size < 1:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    if not isinstance(text, str) or not text.strip():
        return []
    text = text.lstrip("\ufeff")

    sections = _paragraphs_with_sections(text)
    chunks: list[PolicyChunk] = []
    current_text = ""
    current_section: str | None = None
    chunk_number = 0

    for paragraph, section in sections:
        if len(paragraph) > chunk_size:
            if current_text:
                chunks.append(_make_chunk(current_text, current_section, source, document_name, chunk_number, policy_metadata))
                chunk_number += 1
                current_text = ""
            for piece in _split_long_text(paragraph, chunk_size, overlap):
                chunks.append(_make_chunk(piece, section, source, document_name, chunk_number, policy_metadata))
                chunk_number += 1
            current_section = section
            continue

        separator = "\n\n" if current_text else ""
        candidate = f"{current_text}{separator}{paragraph}"
        if current_text and len(candidate) > chunk_size:
            chunks.append(_make_chunk(current_text, current_section, source, document_name, chunk_number, policy_metadata))
            chunk_number += 1
            carry = current_text[-overlap:] if overlap else ""
            current_text = f"{carry}\n\n{paragraph}" if carry else paragraph
            current_section = section or current_section
        else:
            current_text = candidate
            current_section = section or current_section

    if current_text.strip():
        chunks.append(_make_chunk(current_text, current_section, source, document_name, chunk_number, policy_metadata))
    return chunks


def load_policy_documents(
    path: str | Path,
    *,
    chunk_size: int = 1000,
    overlap: int = 100,
) -> list[PolicyChunk]:
    """Load supported policy files from a file or directory recursively.

    Empty documents produce no chunks. Unsupported files are rejected when
    passed directly and ignored when encountered beside supported files in a
    directory.
    """

    document_path = Path(path)
    if not document_path.exists():
        raise FileNotFoundError(f"policy path does not exist: {document_path}")

    if document_path.is_file():
        if document_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise IngestionError(f"unsupported policy file type: {document_path.suffix or '<none>'}")
        return _load_file(document_path, chunk_size, overlap)

    if not document_path.is_dir():
        raise IngestionError(f"policy path is neither a file nor directory: {document_path}")

    files = sorted(
        file_path
        for file_path in document_path.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    chunks: list[PolicyChunk] = []
    for file_path in files:
        chunks.extend(_load_file(file_path, chunk_size, overlap))
    return chunks


def _load_file(path: Path, chunk_size: int, overlap: int) -> list[PolicyChunk]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise IngestionError(f"could not read policy file: {path}") from exc

    policy_metadata = _extract_policy_metadata(text)
    return chunk_text(
        text,
        chunk_size=chunk_size,
        overlap=overlap,
        source=path.name,
        document_name=path.stem,
        policy_metadata=policy_metadata,
    )


def _extract_policy_metadata(text: str) -> dict[str, Any]:
    """Extract the inline metadata header used by the Markdown policy files."""

    metadata: dict[str, Any] = {}
    field_names = {
        "policy id": "policy_id",
        "version": "version",
        "effective date": "effective_date",
        "scope": "scope",
        "region": "region",
        "department": "department",
        "vendor": "vendor",
    }
    for line in text.splitlines():
        match = _POLICY_METADATA_PATTERN.match(line)
        if not match:
            continue
        key = field_names[match.group(1).casefold()]
        value = match.group(2).strip()
        if value:
            metadata[key] = value

        if key == "scope":
            for scope_key, scope_value in re.findall(
                r"\b(region|department|vendor)\s*=\s*([^;,]+)", value, re.IGNORECASE
            ):
                metadata[scope_key.casefold()] = scope_value.strip()
    return metadata


def _paragraphs_with_sections(text: str) -> list[tuple[str, str | None]]:
    paragraphs: list[tuple[str, str | None]] = []
    section: str | None = None
    for block in re.split(r"\n\s*\n+", text.replace("\r\n", "\n").replace("\r", "\n")):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        heading = _HEADING_PATTERN.match(lines[0])
        if heading:
            section = heading.group(1).strip()
            lines = lines[1:]
            if not lines:
                continue
        paragraphs.append(("\n".join(lines).strip(), section))
    return paragraphs


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return pieces


def _make_chunk(
    content: str,
    section: str | None,
    source: str | None,
    document_name: str | None,
    chunk_number: int,
    policy_metadata: Mapping[str, Any] | None = None,
) -> PolicyChunk:
    metadata: dict[str, Any] = {}
    if source:
        metadata["source"] = source
    if document_name:
        metadata["title"] = document_name
    if section:
        metadata["section"] = section
    if policy_metadata:
        metadata.update(policy_metadata)

    chunk: PolicyChunk = {
        "content": content.strip(),
        "metadata": metadata,
        "chunk_id": f"{source or 'document'}#chunk-{chunk_number}",
    }
    if document_name:
        chunk["document_name"] = document_name
    return chunk


__all__ = ["IngestionError", "PolicyChunk", "SUPPORTED_SUFFIXES", "chunk_text", "load_policy_documents"]