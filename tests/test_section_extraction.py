"""Tests for section extraction models, helpers, and the
extract_relevant_section method."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from collector_core.llm.llm_connector import LLMConnector
from collector_core.llm.models import LineRange, SectionExtractionResult


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestLineRange:
    def test_valid(self) -> None:
        lr = LineRange(start=1, end=5)
        assert lr.start == 1
        assert lr.end == 5

    def test_single_line(self) -> None:
        lr = LineRange(start=3, end=3)
        assert lr.start == lr.end == 3

    def test_start_greater_than_end_raises(self) -> None:
        with pytest.raises(ValidationError, match="start.*must be <= end"):
            LineRange(start=10, end=5)

    def test_zero_start_raises(self) -> None:
        with pytest.raises(ValidationError):
            LineRange(start=0, end=5)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            LineRange(start=-1, end=5)

    def test_serialization(self) -> None:
        lr = LineRange(start=2, end=8)
        assert lr.model_dump() == {"start": 2, "end": 8}


class TestSectionExtractionResult:
    def test_relevant_with_lines(self) -> None:
        r = SectionExtractionResult(
            is_relevant=True,
            relevant_lines=[LineRange(start=1, end=10)],
        )
        assert r.is_relevant is True
        assert len(r.relevant_lines) == 1

    def test_not_relevant_empty_lines(self) -> None:
        r = SectionExtractionResult(is_relevant=False, relevant_lines=[])
        assert r.is_relevant is False
        assert r.relevant_lines == []

    def test_not_relevant_default_lines(self) -> None:
        r = SectionExtractionResult(is_relevant=False)
        assert r.relevant_lines == []

    def test_relevant_without_lines_raises(self) -> None:
        with pytest.raises(ValidationError, match="is_relevant is True"):
            SectionExtractionResult(is_relevant=True, relevant_lines=[])

    def test_multiple_ranges(self) -> None:
        r = SectionExtractionResult(
            is_relevant=True,
            relevant_lines=[
                LineRange(start=1, end=5),
                LineRange(start=20, end=30),
            ],
        )
        assert len(r.relevant_lines) == 2

    def test_serialization(self) -> None:
        r = SectionExtractionResult(
            is_relevant=True,
            relevant_lines=[LineRange(start=1, end=3)],
        )
        d = r.model_dump()
        assert d == {
            "is_relevant": True,
            "relevant_lines": [{"start": 1, "end": 3}],
        }


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestNumberLines:
    def test_basic(self) -> None:
        lines = ["alpha", "beta", "gamma", "delta"]
        result = LLMConnector._number_lines(lines, 0, 4)
        assert result == "[1] alpha\n[2] beta\n[3] gamma\n[4] delta"

    def test_slice(self) -> None:
        lines = ["a", "b", "c", "d", "e"]
        result = LLMConnector._number_lines(lines, 2, 4)
        assert result == "[3] c\n[4] d"

    def test_single_line(self) -> None:
        lines = ["only"]
        result = LLMConnector._number_lines(lines, 0, 1)
        assert result == "[1] only"


class TestChunkLines:
    """Test _chunk_lines with a mocked token counter."""

    def _make_connector(self) -> LLMConnector:
        """Create a connector with rate limiting disabled."""
        with patch("collector_core.llm.llm_connector.litellm"):
            connector = LLMConnector.__new__(LLMConnector)
            connector.model = "openai/gpt-4o-mini"
        return connector

    @patch("collector_core.llm.llm_connector.litellm")
    def test_single_chunk(self, mock_litellm: object) -> None:
        """Short document fits in one chunk."""
        import collector_core.llm.llm_connector as mod

        mod.litellm.token_counter = lambda model, text: len(text.split())

        connector = self._make_connector()
        lines = ["word " * 5] * 4  # 4 lines, 5 tokens each = 20 tokens
        chunks = connector._chunk_lines(lines, chunk_size=100, chunk_overlap=10)
        assert chunks == [(0, 4)]

    @patch("collector_core.llm.llm_connector.litellm")
    def test_multiple_chunks(self, mock_litellm: object) -> None:
        """Document split into multiple chunks with overlap."""
        import collector_core.llm.llm_connector as mod

        mod.litellm.token_counter = lambda model, text: len(text.split())

        connector = self._make_connector()
        # 10 lines, 10 tokens each = 100 tokens total
        lines = ["word " * 10] * 10
        chunks = connector._chunk_lines(lines, chunk_size=30, chunk_overlap=10)
        # Should produce multiple chunks
        assert len(chunks) > 1
        # First chunk starts at 0
        assert chunks[0][0] == 0
        # Last chunk ends at 10
        assert chunks[-1][1] == 10

    @patch("collector_core.llm.llm_connector.litellm")
    def test_empty_lines(self, mock_litellm: object) -> None:
        import collector_core.llm.llm_connector as mod

        mod.litellm.token_counter = lambda model, text: len(text.split())

        connector = self._make_connector()
        chunks = connector._chunk_lines([], chunk_size=100, chunk_overlap=10)
        assert chunks == []


# ---------------------------------------------------------------------------
# extract_relevant_section tests (mocked LLM)
# ---------------------------------------------------------------------------


class TestExtractRelevantSection:
    """Integration tests with mocked LLM calls."""

    def _make_connector(self) -> LLMConnector:
        connector = LLMConnector.__new__(LLMConnector)
        connector.model = "openai/gpt-4o-mini"
        connector.api_key = None
        connector.temperature = 0.1
        connector.timeout_seconds = 60.0
        connector.max_retries = 1
        connector._rate_limiter = None
        connector._instructor_client = None
        return connector

    @pytest.mark.asyncio
    async def test_short_document_passes_through(self) -> None:
        """Documents below token threshold are returned unchanged."""
        connector = self._make_connector()
        text = "Kurzer Text zum Thema."

        with patch(
            "collector_core.llm.llm_connector.litellm.token_counter",
            return_value=10,
        ):
            result = await connector.extract_relevant_section(
                text=text,
                vorgang_titel="Schulgesetz",
                token_threshold=30_000,
            )

        assert result == text

    @pytest.mark.asyncio
    async def test_relevant_lines_extracted(self) -> None:
        """Relevant line ranges are extracted verbatim from source."""
        connector = self._make_connector()
        lines = [f"Zeile {i}" for i in range(1, 21)]
        text = "\n".join(lines)

        mock_result = SectionExtractionResult(
            is_relevant=True,
            relevant_lines=[LineRange(start=5, end=8)],
        )

        with (
            patch(
                "collector_core.llm.llm_connector.litellm.token_counter",
                return_value=50_000,
            ),
            patch.object(
                connector,
                "_chunk_lines",
                return_value=[(0, 20)],
            ),
            patch.object(
                connector,
                "extract",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            result = await connector.extract_relevant_section(
                text=text,
                vorgang_titel="Schulgesetz",
                token_threshold=30_000,
            )

        assert result is not None
        expected = "\n".join(lines[4:8])  # 0-based: indices 4,5,6,7
        assert result == expected

    @pytest.mark.asyncio
    async def test_no_relevant_content_returns_none(self) -> None:
        """Returns None when no chunk has relevant content."""
        connector = self._make_connector()
        text = "\n".join([f"Zeile {i}" for i in range(1, 11)])

        mock_result = SectionExtractionResult(
            is_relevant=False, relevant_lines=[]
        )

        with (
            patch(
                "collector_core.llm.llm_connector.litellm.token_counter",
                return_value=50_000,
            ),
            patch.object(
                connector,
                "_chunk_lines",
                return_value=[(0, 10)],
            ),
            patch.object(
                connector,
                "extract",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            result = await connector.extract_relevant_section(
                text=text,
                vorgang_titel="Schulgesetz",
                token_threshold=30_000,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_early_stopping(self) -> None:
        """Processing stops after consecutive irrelevant chunks."""
        connector = self._make_connector()
        text = "\n".join([f"Zeile {i}" for i in range(1, 51)])

        irrelevant = SectionExtractionResult(
            is_relevant=False, relevant_lines=[]
        )

        mock_extract = AsyncMock(return_value=irrelevant)

        with (
            patch(
                "collector_core.llm.llm_connector.litellm.token_counter",
                return_value=50_000,
            ),
            patch.object(
                connector,
                "_chunk_lines",
                return_value=[(0, 10), (8, 20), (18, 30), (28, 40), (38, 50)],
            ),
            patch.object(connector, "extract", mock_extract),
        ):
            result = await connector.extract_relevant_section(
                text=text,
                vorgang_titel="Schulgesetz",
                token_threshold=30_000,
                early_stop_after=3,
            )

        assert result is None
        # Should have stopped after 3 irrelevant chunks, not processed all 5
        assert mock_extract.call_count == 3

    @pytest.mark.asyncio
    async def test_clamped_line_ranges(self) -> None:
        """Line ranges outside the chunk boundaries are clamped."""
        connector = self._make_connector()
        lines = [f"Zeile {i}" for i in range(1, 11)]
        text = "\n".join(lines)

        # LLM returns range extending beyond chunk (lines 1-10, but claims 1-15)
        mock_result = SectionExtractionResult(
            is_relevant=True,
            relevant_lines=[LineRange(start=1, end=15)],
        )

        with (
            patch(
                "collector_core.llm.llm_connector.litellm.token_counter",
                return_value=50_000,
            ),
            patch.object(
                connector,
                "_chunk_lines",
                return_value=[(0, 10)],
            ),
            patch.object(
                connector,
                "extract",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            result = await connector.extract_relevant_section(
                text=text,
                vorgang_titel="Schulgesetz",
                token_threshold=30_000,
            )

        # Should clamp to available lines (1-10)
        assert result is not None
        assert result == "\n".join(lines)

    @pytest.mark.asyncio
    async def test_multiple_ranges_merged(self) -> None:
        """Overlapping ranges across chunks are deduplicated."""
        connector = self._make_connector()
        lines = [f"Zeile {i}" for i in range(1, 21)]
        text = "\n".join(lines)

        # chunk1 sees lines 1-10, identifies 3-10 as relevant
        result_chunk1 = SectionExtractionResult(
            is_relevant=True,
            relevant_lines=[LineRange(start=3, end=10)],
        )
        # chunk2 sees lines 9-20, identifies 9-14 as relevant
        # (overlap region: lines 9-10 appear in both chunks)
        result_chunk2 = SectionExtractionResult(
            is_relevant=True,
            relevant_lines=[LineRange(start=9, end=14)],
        )

        with (
            patch(
                "collector_core.llm.llm_connector.litellm.token_counter",
                return_value=50_000,
            ),
            patch.object(
                connector,
                "_chunk_lines",
                return_value=[(0, 10), (8, 20)],
            ),
            patch.object(
                connector,
                "extract",
                new_callable=AsyncMock,
                side_effect=[result_chunk1, result_chunk2],
            ),
        ):
            result = await connector.extract_relevant_section(
                text=text,
                vorgang_titel="Schulgesetz",
                token_threshold=30_000,
            )

        assert result is not None
        # Lines 3-14 (1-based) = indices 2-13, deduplicated at overlap
        expected = "\n".join(lines[2:14])
        assert result == expected

    @pytest.mark.asyncio
    async def test_empty_text_raises(self) -> None:
        connector = self._make_connector()
        with pytest.raises(ValueError, match="text must not be empty"):
            await connector.extract_relevant_section(
                text="", vorgang_titel="Test"
            )

    @pytest.mark.asyncio
    async def test_empty_titel_raises(self) -> None:
        connector = self._make_connector()
        with pytest.raises(ValueError, match="vorgang_titel must not be empty"):
            await connector.extract_relevant_section(
                text="Some text", vorgang_titel=""
            )

    @pytest.mark.asyncio
    async def test_invalid_chunk_size_raises(self) -> None:
        connector = self._make_connector()
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            await connector.extract_relevant_section(
                text="Some text", vorgang_titel="Test", chunk_size=0
            )

    @pytest.mark.asyncio
    async def test_overlap_ge_chunk_size_raises(self) -> None:
        connector = self._make_connector()
        with pytest.raises(
            ValueError, match="chunk_overlap must be less than chunk_size"
        ):
            await connector.extract_relevant_section(
                text="Some text",
                vorgang_titel="Test",
                chunk_size=1000,
                chunk_overlap=1000,
            )

    @pytest.mark.asyncio
    async def test_invalid_token_threshold_raises(self) -> None:
        connector = self._make_connector()
        with pytest.raises(ValueError, match="token_threshold must be positive"):
            await connector.extract_relevant_section(
                text="Some text", vorgang_titel="Test", token_threshold=0
            )

    @pytest.mark.asyncio
    async def test_vnr_included_in_prompt(self) -> None:
        """When vorgang_vnr is given, it appears in the prompt."""
        connector = self._make_connector()
        text = "Kurzer Text."

        calls: list[str] = []
        original_extract = AsyncMock(
            return_value=SectionExtractionResult(
                is_relevant=False, relevant_lines=[]
            )
        )

        async def capture_extract(prompt: str, **kwargs: object) -> object:
            calls.append(prompt)
            return await original_extract(prompt, **kwargs)

        with (
            patch(
                "collector_core.llm.llm_connector.litellm.token_counter",
                return_value=50_000,
            ),
            patch.object(
                connector,
                "_chunk_lines",
                return_value=[(0, 1)],
            ),
            patch.object(connector, "extract", side_effect=capture_extract),
        ):
            await connector.extract_relevant_section(
                text=text,
                vorgang_titel="Schulgesetz",
                vorgang_vnr="7/1234",
                token_threshold=30_000,
            )

        assert len(calls) == 1
        assert "Drucksache 7/1234" in calls[0]
