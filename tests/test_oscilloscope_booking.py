"""
Test script to verify lab rules retrieval for the query:
"Can I book an oscilloscope from 4 PM to 6 PM?"
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rag.rag_pipeline import LabRAGPipeline, get_rag_pipeline, retrieve_lab_rules


def test_oscilloscope_query():
    print("=" * 80)
    print("TEST: RAG Rule Retrieval for Oscilloscope Booking Query")
    print("=" * 80)
    
    query = "Can I book an oscilloscope from 4 PM to 6 PM?"
    print(f"Query: \"{query}\"\n")
    
    # Retrieve top 4 relevant rule documents via retrieve_lab_rules
    retrieved_docs = retrieve_lab_rules(query, k=4)
    
    print(f"Total Rules Retrieved: {len(retrieved_docs)}\n")
    for idx, doc in enumerate(retrieved_docs, start=1):
        source = doc.metadata.get("source", "Unknown")
        section = doc.metadata.get("section", "General")
        sub_section = doc.metadata.get("sub_section", "")
        chunk_id = doc.metadata.get("chunk_id", "")
        
        print(f"--- Rule Citation [{idx}] ---")
        print(f"Source File : {source}")
        print(f"Section     : {section}")
        if sub_section:
            print(f"Sub-Section : {sub_section}")
        print(f"Chunk ID    : {chunk_id}")
        print("Content:")
        print(doc.page_content)
        print("-" * 80)
        
    return retrieved_docs


class TestOscilloscopeRuleRetrieval(unittest.TestCase):
    """Unit test case for oscilloscope query retrieval."""

    def setUp(self):
        self.rag = get_rag_pipeline()
        self.query = "Can I book an oscilloscope from 4 PM to 6 PM?"

    def test_retrieve_lab_rules_function(self):
        """Verify retrieve_lab_rules direct function and method work identically."""
        docs_func = retrieve_lab_rules(self.query, k=4)
        docs_method = self.rag.retrieve_lab_rules(self.query, k=4)
        self.assertEqual(len(docs_func), 4)
        self.assertEqual(len(docs_method), 4)
        self.assertEqual(docs_func[0].page_content, docs_method[0].page_content)

    def test_retrieval_covers_all_required_facets(self):
        """Verify retrieval captures operating hours, oscilloscope rules, duration, and approval."""
        docs = retrieve_lab_rules(self.query, k=4)
        self.assertGreaterEqual(len(docs), 3, "Should retrieve at least 3 relevant rule chunks.")
        
        combined_text = " ".join([d.page_content for d in docs]).lower()

        # 1. Oscilloscope specific booking & rules
        self.assertIn("oscilloscope", combined_text)
        
        # 2. Operating hours (08:00 - 20:00 or PM)
        self.assertTrue(
            "operating hours" in combined_text or "08:00" in combined_text or "20:00" in combined_text or "4 pm" in combined_text,
            "Must retrieve laboratory operating hours rules."
        )

        # 3. Duration limits (30 min / 2 hours / 3 hours)
        self.assertTrue(
            "duration" in combined_text or "3 continuous hours" in combined_text or "2 hours" in combined_text,
            "Must retrieve session duration limits."
        )

        # 4. Approval requirements (no supervisor approval needed / automatic approval)
        self.assertTrue(
            "approval" in combined_text or "supervisor" in combined_text or "approved" in combined_text,
            "Must retrieve approval requirements."
        )


if __name__ == "__main__":
    # Execute print demo
    test_oscilloscope_query()
    
    # Run unit test
    print("\nRunning unittest:")
    unittest.main()

