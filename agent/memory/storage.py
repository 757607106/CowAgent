"""PostgreSQL storage layer for long-term memory search."""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.log import logger
from cow_platform.db import connect, jsonb


@dataclass
class MemoryChunk:
    """Represents a memory chunk with text and embedding."""

    id: str
    user_id: Optional[str]
    scope: str
    source: str
    path: str
    start_line: int
    end_line: int
    text: str
    embedding: Optional[List[float]]
    hash: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    """Search result with score and snippet."""

    path: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    source: str
    user_id: Optional[str] = None


class MemoryStorage:
    """PostgreSQL-backed memory chunk storage.

    The constructor still accepts the historical db_path argument, but the path is
    now only used to derive a stable PostgreSQL namespace.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.namespace = hashlib.sha256(str(Path(db_path)).encode("utf-8")).hexdigest()

    def save_chunk(self, chunk: MemoryChunk):
        self.save_chunks_batch([chunk])

    def save_chunks_batch(self, chunks: List[MemoryChunk]):
        if not chunks:
            return
        now = int(time.time())
        with connect() as conn:
            use_pgvector = self._has_pgvector_column(conn)
            with conn.transaction():
                for chunk in chunks:
                    if use_pgvector:
                        conn.execute(
                            """
                            INSERT INTO platform_memory_chunks
                                (namespace, id, user_id, scope, source, path, start_line,
                                 end_line, text, embedding, embedding_vector, hash, metadata, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s)
                            ON CONFLICT (namespace, id)
                            DO UPDATE SET
                                user_id = EXCLUDED.user_id,
                                scope = EXCLUDED.scope,
                                source = EXCLUDED.source,
                                path = EXCLUDED.path,
                                start_line = EXCLUDED.start_line,
                                end_line = EXCLUDED.end_line,
                                text = EXCLUDED.text,
                                embedding = EXCLUDED.embedding,
                                embedding_vector = EXCLUDED.embedding_vector,
                                hash = EXCLUDED.hash,
                                metadata = EXCLUDED.metadata,
                                updated_at = EXCLUDED.updated_at
                            """,
                            (
                                self.namespace,
                                chunk.id,
                                chunk.user_id,
                                chunk.scope,
                                chunk.source,
                                chunk.path,
                                chunk.start_line,
                                chunk.end_line,
                                chunk.text,
                                jsonb(chunk.embedding) if chunk.embedding else None,
                                self._pgvector_literal(chunk.embedding),
                                chunk.hash,
                                jsonb(chunk.metadata) if chunk.metadata else None,
                                now,
                                now,
                            ),
                        )
                    else:
                        conn.execute(
                            """
                            INSERT INTO platform_memory_chunks
                                (namespace, id, user_id, scope, source, path, start_line,
                                 end_line, text, embedding, hash, metadata, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (namespace, id)
                            DO UPDATE SET
                                user_id = EXCLUDED.user_id,
                                scope = EXCLUDED.scope,
                                source = EXCLUDED.source,
                                path = EXCLUDED.path,
                                start_line = EXCLUDED.start_line,
                                end_line = EXCLUDED.end_line,
                                text = EXCLUDED.text,
                                embedding = EXCLUDED.embedding,
                                hash = EXCLUDED.hash,
                                metadata = EXCLUDED.metadata,
                                updated_at = EXCLUDED.updated_at
                            """,
                            (
                                self.namespace,
                                chunk.id,
                                chunk.user_id,
                                chunk.scope,
                                chunk.source,
                                chunk.path,
                                chunk.start_line,
                                chunk.end_line,
                                chunk.text,
                                jsonb(chunk.embedding) if chunk.embedding else None,
                                chunk.hash,
                                jsonb(chunk.metadata) if chunk.metadata else None,
                                now,
                                now,
                            ),
                        )

    def get_chunk(self, chunk_id: str) -> Optional[MemoryChunk]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM platform_memory_chunks
                WHERE namespace = %s AND id = %s
                """,
                (self.namespace, chunk_id),
            ).fetchone()
        return self._row_to_chunk(row) if row else None

    def search_vector(
        self,
        query_embedding: List[float],
        user_id: Optional[str] = None,
        scopes: List[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        scopes = self._resolve_scopes(user_id, scopes)
        with connect() as conn:
            if self._has_pgvector_column(conn):
                try:
                    pgvector_results = self._search_vector_pgvector(
                        conn,
                        query_embedding=query_embedding,
                        user_id=user_id,
                        scopes=scopes,
                        limit=limit,
                    )
                    if len(pgvector_results) >= max(1, int(limit)):
                        return pgvector_results
                    jsonb_results = self._search_vector_jsonb(
                        conn,
                        query_embedding=query_embedding,
                        user_id=user_id,
                        scopes=scopes,
                        limit=limit,
                    )
                    return self._merge_vector_results(pgvector_results, jsonb_results, limit)
                except Exception as e:
                    logger.warning(f"[MemoryStorage] pgvector search failed, fallback to JSONB embeddings: {e}")
            return self._search_vector_jsonb(
                conn,
                query_embedding=query_embedding,
                user_id=user_id,
                scopes=scopes,
                limit=limit,
            )

    def _search_vector_pgvector(
        self,
        conn,
        *,
        query_embedding: List[float],
        user_id: Optional[str],
        scopes: List[str],
        limit: int,
    ) -> List[SearchResult]:
        vector_literal = self._pgvector_literal(query_embedding)
        if not vector_literal:
            return []
        params: list[Any] = [vector_literal, self.namespace, scopes]
        user_filter = ""
        if user_id:
            user_filter = "AND (scope = 'shared' OR user_id = %s)"
            params.append(user_id)
        params.extend([vector_literal, max(1, int(limit))])
        rows = conn.execute(
            f"""
            SELECT *,
                   GREATEST(0, 1 - (embedding_vector <=> %s::vector)) AS vector_score
            FROM platform_memory_chunks
            WHERE namespace = %s
              AND scope = ANY(%s)
              AND embedding_vector IS NOT NULL
              {user_filter}
            ORDER BY embedding_vector <=> %s::vector
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()
        return [
            SearchResult(
                path=row["path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                score=float(row["vector_score"] or 0),
                snippet=self._truncate_text(row["text"], 500),
                source=row["source"],
                user_id=row["user_id"],
            )
            for row in rows
            if float(row["vector_score"] or 0) > 0
        ]

    def _search_vector_jsonb(
        self,
        conn,
        *,
        query_embedding: List[float],
        user_id: Optional[str],
        scopes: List[str],
        limit: int,
    ) -> List[SearchResult]:
        params: list[Any] = [self.namespace, scopes]
        user_filter = ""
        if user_id:
            user_filter = "AND (scope = 'shared' OR user_id = %s)"
            params.append(user_id)
        rows = conn.execute(
            f"""
            SELECT *
            FROM platform_memory_chunks
            WHERE namespace = %s
              AND scope = ANY(%s)
              AND embedding IS NOT NULL
              {user_filter}
            """,
            tuple(params),
        ).fetchall()

        results = []
        for row in rows:
            similarity = self._cosine_similarity(query_embedding, row["embedding"] or [])
            if similarity > 0:
                results.append((similarity, row))
        results.sort(key=lambda item: item[0], reverse=True)
        return [
            SearchResult(
                path=row["path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                score=score,
                snippet=self._truncate_text(row["text"], 500),
                source=row["source"],
                user_id=row["user_id"],
            )
            for score, row in results[:limit]
        ]

    @staticmethod
    def _merge_vector_results(
        primary: List[SearchResult],
        fallback: List[SearchResult],
        limit: int,
    ) -> List[SearchResult]:
        merged: dict[tuple[str, int, int, str, Optional[str]], SearchResult] = {}
        for result in [*primary, *fallback]:
            key = (result.path, result.start_line, result.end_line, result.source, result.user_id)
            existing = merged.get(key)
            if existing is None or result.score > existing.score:
                merged[key] = result
        return sorted(merged.values(), key=lambda item: item.score, reverse=True)[: max(1, int(limit))]

    def search_keyword(
        self,
        query: str,
        user_id: Optional[str] = None,
        scopes: List[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        scopes = self._resolve_scopes(user_id, scopes)
        tokens = self._extract_search_tokens(query)
        if not tokens:
            return []
        like_clauses = " OR ".join(["text ILIKE %s" for _ in tokens])
        params: list[Any] = [self.namespace, scopes, *[f"%{token}%" for token in tokens]]
        user_filter = ""
        if user_id:
            user_filter = "AND (scope = 'shared' OR user_id = %s)"
            params.append(user_id)
        params.append(max(1, int(limit)))
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM platform_memory_chunks
                WHERE namespace = %s
                  AND scope = ANY(%s)
                  AND ({like_clauses})
                  {user_filter}
                LIMIT %s
                """,
                tuple(params),
            ).fetchall()
        return [
            SearchResult(
                path=row["path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                score=0.5,
                snippet=self._truncate_text(row["text"], 500),
                source=row["source"],
                user_id=row["user_id"],
            )
            for row in rows
        ]

    def delete_by_path(self, path: str):
        with connect() as conn:
            conn.execute(
                "DELETE FROM platform_memory_chunks WHERE namespace = %s AND path = %s",
                (self.namespace, path),
            )
            conn.commit()

    def get_file_hash(self, path: str) -> Optional[str]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT hash
                FROM platform_memory_files
                WHERE namespace = %s AND path = %s
                """,
                (self.namespace, path),
            ).fetchone()
        return row["hash"] if row else None

    def update_file_metadata(self, path: str, source: str, file_hash: str, mtime: int, size: int):
        now = int(time.time())
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO platform_memory_files
                    (namespace, path, source, hash, mtime, size, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (namespace, path)
                DO UPDATE SET
                    source = EXCLUDED.source,
                    hash = EXCLUDED.hash,
                    mtime = EXCLUDED.mtime,
                    size = EXCLUDED.size,
                    updated_at = EXCLUDED.updated_at
                """,
                (self.namespace, path, source, file_hash, int(mtime), int(size), now),
            )
            conn.commit()

    def get_stats(self) -> Dict[str, int]:
        with connect() as conn:
            chunks_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM platform_memory_chunks WHERE namespace = %s",
                (self.namespace,),
            ).fetchone()["cnt"]
            files_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM platform_memory_files WHERE namespace = %s",
                (self.namespace,),
            ).fetchone()["cnt"]
        return {"chunks": int(chunks_count), "files": int(files_count)}

    def close(self):
        return None

    def _row_to_chunk(self, row) -> MemoryChunk:
        return MemoryChunk(
            id=row["id"],
            user_id=row["user_id"],
            scope=row["scope"],
            source=row["source"],
            path=row["path"],
            start_line=row["start_line"],
            end_line=row["end_line"],
            text=row["text"],
            embedding=row["embedding"] if row["embedding"] else None,
            hash=row["hash"],
            metadata=row["metadata"] if row["metadata"] else None,
        )

    @staticmethod
    def _resolve_scopes(user_id: Optional[str], scopes: List[str] | None) -> List[str]:
        if scopes is not None:
            return scopes
        resolved = ["shared"]
        if user_id:
            resolved.append("user")
        return resolved

    @staticmethod
    def _extract_search_tokens(query: str) -> List[str]:
        cjk_words = re.findall(r"[\u4e00-\u9fff]{2,}", query)
        latin_words = re.findall(r"[A-Za-z0-9_]+", query)
        return [token for token in [*cjk_words, *latin_words] if token]

    @staticmethod
    def _has_pgvector_column(conn) -> bool:
        try:
            row = conn.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'platform_memory_chunks'
                      AND column_name = 'embedding_vector'
                ) AS exists
                """
            ).fetchone()
            return bool(row and row["exists"])
        except Exception:
            return False

    @staticmethod
    def _pgvector_literal(embedding: Optional[List[float]]) -> Optional[str]:
        if not embedding:
            return None
        values: list[str] = []
        for item in embedding:
            try:
                value = float(item)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(value):
                return None
            values.append(format(value, ".12g"))
        return "[" + ",".join(values) + "]"

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        if len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    @staticmethod
    def _truncate_text(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
