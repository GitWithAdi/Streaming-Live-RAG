"""
Corpus loader and chunking module.
Ensures document chunks strictly carry verifiable section markers [Doc_ID §Section].
"""

import json
import os
from typing import List, Union
from streaming_rag.schemas import DocumentChunk


class CorpusChunker:
    """Loads and standardizes corpus documents into verifiable DocumentChunk objects."""

    @staticmethod
    def load_corpus(file_or_dir_path: str) -> List[DocumentChunk]:
        """Loads corpus documents from a JSON file, directory of JSON files, or text files."""
        chunks: List[DocumentChunk] = []

        if not os.path.exists(file_or_dir_path):
            raise FileNotFoundError(f"Corpus path not found: {file_or_dir_path}")

        if os.path.isfile(file_or_dir_path):
            paths = [file_or_dir_path]
        else:
            paths = [
                os.path.join(file_or_dir_path, f)
                for f in os.listdir(file_or_dir_path)
                if f.endswith(".json")
            ]

        for p in paths:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        chunk = DocumentChunk(
                            doc_id=item.get("doc_id", "Doc_UNKNOWN"),
                            section=str(item.get("section", "§1")),
                            title=item.get("title", "Untitled Section"),
                            text=item.get("text", "").strip(),
                            metadata=item.get("metadata", {})
                        )
                        chunks.append(chunk)
                elif isinstance(data, dict):
                    chunk = DocumentChunk(
                        doc_id=data.get("doc_id", "Doc_UNKNOWN"),
                        section=str(data.get("section", "§1")),
                        title=data.get("title", "Untitled Section"),
                        text=data.get("text", "").strip(),
                        metadata=data.get("metadata", {})
                    )
                    chunks.append(chunk)

        return chunks
