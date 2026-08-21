"""
RAG Pipeline for Smart Laboratory Resource Agent.
Loads laboratory rules, equipment specifications, and booking policies,
creates embeddings, stores them in an InMemoryVectorStore, and retrieves relevant rules.
"""

import os
import re
import hashlib
from typing import List, Optional, Tuple, Dict, Any
import numpy as np

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore


class LocalSemanticEmbeddings(Embeddings):
    """
    Lightweight, deterministic local semantic embedding engine.
    Uses word n-grams, character 3-grams, time normalization, and normalized projection.
    Zero external API calls, zero rate-limits, ultra-fast for hackathons.
    """

    STOP_WORDS = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "with",
        "is", "are", "was", "were", "be", "been", "can", "could", "would",
        "should", "do", "does", "did", "i", "you", "he", "she", "it", "we", "they",
        "from", "by", "as", "into", "through", "about"
    }

    def __init__(self, dim: int = 512):
        self.dim = dim

    def _normalize_time_tokens(self, text: str) -> str:
        """Expands 12h/24h time expressions (e.g. 4 PM -> 4 pm 16:00 4pm) for cross-format matching."""
        text_mod = text.lower()
        time_matches = re.findall(r"\b(\d{1,2})\s*(am|pm)\b", text_mod)
        expansions = []
        for hr, period in time_matches:
            hr_int = int(hr)
            if period == "pm" and hr_int != 12:
                hr_24 = hr_int + 12
            elif period == "am" and hr_int == 12:
                hr_24 = 0
            else:
                hr_24 = hr_int
            expansions.append(f"{hr_24:02d}:00")
            expansions.append(f"{hr}{period}")
        if expansions:
            text_mod += " " + " ".join(expansions)
        return text_mod

    def _tokenize(self, text: str) -> List[Tuple[str, float]]:
        expanded = self._normalize_time_tokens(text)
        clean = re.sub(r"[^\w\s]", " ", expanded.lower())
        tokens = clean.split()
        
        weighted_features: List[Tuple[str, float]] = []

        # Unigrams with stop-word attenuation
        for token in tokens:
            weight = 0.3 if token in self.STOP_WORDS else 1.5
            weighted_features.append((token, weight))

        # Word bigrams for phrase and context capture
        for i in range(len(tokens) - 1):
            w1, w2 = tokens[i], tokens[i+1]
            weight = 0.6 if (w1 in self.STOP_WORDS and w2 in self.STOP_WORDS) else 2.0
            weighted_features.append((f"{w1}_{w2}", weight))

        # Character tri-grams for subword / morphological matching
        for token in tokens:
            if len(token) >= 3 and token not in self.STOP_WORDS:
                for j in range(len(token) - 2):
                    weighted_features.append((f"#{token[j:j+3]}", 0.75))

        return weighted_features

    def _embed_single(self, text: str) -> List[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        features = self._tokenize(text)
        if not features:
            return vec.tolist()

        for feat, weight in features:
            # Deterministic hash to dimension index
            idx = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[idx] += weight

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text)


class LabRAGPipeline:
    """
    LangChain RAG Pipeline for Laboratory Rules & Policies.
    Loads knowledge base documents, chunks by logical section,
    indexes into an InMemoryVectorStore, and provides rule retrieval.
    """

    def __init__(
        self,
        docs_dir: Optional[str] = None,
        embedding_type: str = "local",
        openai_api_key: Optional[str] = None,
    ):
        if docs_dir is None:
            self.docs_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.docs_dir = docs_dir

        self.embedding_type = embedding_type
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")

        # Initialize Embeddings
        if self.embedding_type == "openai" and self.openai_api_key:
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_api_key)
        else:
            self.embeddings = LocalSemanticEmbeddings()

        self.vector_store: Optional[InMemoryVectorStore] = None
        self.documents: List[Document] = []
        self._initialize_pipeline()

    def _initialize_pipeline(self) -> None:
        """Loads documents, chunks them, and builds the in-memory vector store."""
        raw_docs = self._load_documents()
        self.documents = self._chunk_documents(raw_docs)
        self.vector_store = InMemoryVectorStore(self.embeddings)
        if self.documents:
            self.vector_store.add_documents(self.documents)

    def _load_documents(self) -> List[Dict[str, Any]]:
        """Loads all .txt rule files from the rag directory."""
        loaded_files = []
        target_files = ["lab_rules.txt", "equipment_rules.txt", "booking_policy.txt"]

        for filename in target_files:
            file_path = os.path.join(self.docs_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    loaded_files.append({"file_name": filename, "content": content})
            else:
                # Search dynamically for any .txt in docs_dir if specific file missing
                pass

        if not loaded_files:
            # Fallback: scan all .txt files in docs_dir
            for entry in os.listdir(self.docs_dir):
                if entry.endswith(".txt"):
                    path = os.path.join(self.docs_dir, entry)
                    with open(path, "r", encoding="utf-8") as f:
                        loaded_files.append({"file_name": entry, "content": f.read()})

        return loaded_files

    def _chunk_documents(self, raw_files: List[Dict[str, Any]]) -> List[Document]:
        """
        Splits documents by logical SECTION or numbered sub-sections
        while preserving rich metadata (source, section title, topics).
        """
        chunks = []
        for file_data in raw_files:
            file_name = file_data["file_name"]
            content = file_data["content"]

            # Split by SECTION headers or double newlines
            sections = re.split(r"(?=SECTION\s+\d+:)", content)
            
            for sec_idx, section in enumerate(sections):
                cleaned_sec = section.strip()
                if not cleaned_sec:
                    continue

                # Check if section has sub-sections (e.g., 1.1, 1.2, 2.1)
                sub_parts = re.split(r"(?=\n\d+\.\d+\s+)", cleaned_sec)
                
                # Extract main section title
                first_line = cleaned_sec.splitlines()[0] if cleaned_sec.splitlines() else f"Section {sec_idx}"
                main_title = first_line.replace("#", "").strip()

                if len(sub_parts) > 1:
                    # Header intro
                    header_intro = sub_parts[0].strip()
                    for sub_idx, sub in enumerate(sub_parts[1:], 1):
                        sub_text = sub.strip()
                        sub_title = sub_text.splitlines()[0] if sub_text.splitlines() else f"Part {sub_idx}"
                        full_content = f"[{file_name} > {main_title}]\n{sub_text}"
                        
                        doc = Document(
                            page_content=full_content,
                            metadata={
                                "source": file_name,
                                "section": main_title,
                                "sub_section": sub_title,
                                "chunk_id": f"{file_name}_sec{sec_idx}_part{sub_idx}",
                            },
                        )
                        chunks.append(doc)
                else:
                    doc = Document(
                        page_content=f"[{file_name} > {main_title}]\n{cleaned_sec}",
                        metadata={
                            "source": file_name,
                            "section": main_title,
                            "chunk_id": f"{file_name}_sec{sec_idx}",
                        },
                    )
                    chunks.append(doc)

        return chunks

    def retrieve_relevant_rules(self, query: str, k: int = 3) -> List[Document]:
        """Retrieves top-k most relevant rule documents for a query."""
        if not self.vector_store:
            return []
        return self.vector_store.similarity_search(query, k=k)

    def retrieve_lab_rules(self, query: str, k: int = 3) -> List[Document]:
        """Direct alias for retrieving top-k relevant laboratory rule documents."""
        return self.retrieve_relevant_rules(query, k=k)

    def retrieve_with_scores(self, query: str, k: int = 3) -> List[Tuple[Document, float]]:
        """Retrieves top-k rules with similarity scores."""
        if not self.vector_store:
            return []
        return self.vector_store.similarity_search_with_score(query, k=k)

    def get_rules_context(self, query: str, k: int = 3) -> str:
        """
        Retrieves rules and formats them as a clean string suitable for
        agent prompts or auditor reasoning.
        """
        docs = self.retrieve_relevant_rules(query, k=k)
        if not docs:
            return "No relevant laboratory rules found."

        formatted_rules = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Unknown")
            section = doc.metadata.get("section", "General")
            formatted_rules.append(
                f"--- Rule Citation [{i}] (Source: {source} | {section}) ---\n{doc.page_content}"
            )
        return "\n\n".join(formatted_rules)


# Module-level singleton helper
_DEFAULT_RAG_PIPELINE: Optional[LabRAGPipeline] = None

def get_rag_pipeline(docs_dir: Optional[str] = None) -> LabRAGPipeline:
    """Returns or creates the shared default RAG pipeline instance."""
    global _DEFAULT_RAG_PIPELINE
    if _DEFAULT_RAG_PIPELINE is None or (docs_dir and docs_dir != _DEFAULT_RAG_PIPELINE.docs_dir):
        _DEFAULT_RAG_PIPELINE = LabRAGPipeline(docs_dir=docs_dir)
    return _DEFAULT_RAG_PIPELINE


def retrieve_lab_rules(query: str, k: int = 3, docs_dir: Optional[str] = None) -> List[Document]:
    """
    Direct functional entry point to retrieve laboratory rules using the default RAG pipeline.
    """
    pipeline = get_rag_pipeline(docs_dir=docs_dir)
    return pipeline.retrieve_lab_rules(query, k=k)

