"""
Advanced RAG Examples using Producer AI Agent
Based on RAG Zero to Hero Guide best practices
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.r2r_client import R2RClient, Document
from src.rag_advanced import (
    AdvancedRAGPipeline,
    RAGStrategy,
    RerankingMethod,
    HybridSearchConfig,
    GraphRAGConfig,
    AdvancedChunker
)
from src.music_fsm import MusicGenerationFSM
from src.api_client import AIMusicAPIClient
from src.models import MusicGenerationRequest
from src.logger import setup_logging


# Setup logging
setup_logging(log_level="INFO")


async def example_1_hybrid_search():
    """
    Example 1: Hybrid Search with Semantic + Keyword

    Best for: General purpose search with diverse queries
    """
    print("\n" + "="*60)
    print("Example 1: Hybrid Search (Semantic + Keyword)")
    print("="*60 + "\n")

    # Initialize R2R client
    r2r = R2RClient(base_url="http://localhost:7272")

    # Create advanced RAG pipeline with hybrid search
    rag_pipeline = AdvancedRAGPipeline(
        r2r_client=r2r,
        strategy=RAGStrategy.HYBRID,
        reranking=RerankingMethod.LLM_BASED,
        hybrid_config=HybridSearchConfig(
            semantic_weight=0.7,
            keyword_weight=0.3,
            fusion_method="reciprocal_rank"
        )
    )

    # Ingest sample documents about music production
    documents = [
        Document(
            content="Electronic dance music (EDM) typically features a tempo between 120-140 BPM with heavy emphasis on bass and synthesizers.",
            title="EDM Characteristics",
            metadata={"category": "music_theory", "genre": "edm"}
        ),
        Document(
            content="Hip-hop production often uses sampling, 808 drum machines, and boom-bap rhythms with BPM around 80-110.",
            title="Hip-Hop Production",
            metadata={"category": "music_theory", "genre": "hip-hop"}
        ),
        Document(
            content="Ambient music focuses on atmospheric sounds, minimal percussion, and evolving textures to create immersive soundscapes.",
            title="Ambient Music",
            metadata={"category": "music_theory", "genre": "ambient"}
        )
    ]

    # Ingest documents
    print("Ingesting documents...")
    await r2r.ingest_documents(documents, collection_id="music-knowledge")

    # Perform hybrid search query
    print("\nExecuting hybrid search...")
    result = await rag_pipeline.query(
        query="What are the characteristics of electronic dance music?",
        collection_id="music-knowledge",
        limit=5,
        use_query_expansion=True,
        use_reranking=True
    )

    # Display results
    print(f"\nAnswer: {result['answer']}\n")
    print(f"Strategy: {result['strategy']}")
    print(f"Number of sources: {result['metadata']['num_sources']}")
    print(f"\nEvaluation:")
    print(f"  - Groundedness: {result['evaluation']['groundedness_score']:.2f}")
    print(f"  - Confidence: {result['evaluation']['confidence']:.2f}")
    print(f"  - Hallucination detected: {result['evaluation']['hallucination_detected']}")

    print("\nTop sources:")
    for i, source in enumerate(result['sources'][:3], 1):
        print(f"  {i}. {source.title} (score: {source.score:.3f})")
        print(f"     {source.content[:100]}...")


async def example_2_graphrag():
    """
    Example 2: GraphRAG with Knowledge Graphs

    Best for: Complex queries requiring entity relationships
    """
    print("\n" + "="*60)
    print("Example 2: GraphRAG with Knowledge Graphs")
    print("="*60 + "\n")

    r2r = R2RClient(base_url="http://localhost:7272")

    # Create GraphRAG pipeline
    rag_pipeline = AdvancedRAGPipeline(
        r2r_client=r2r,
        strategy=RAGStrategy.GRAPH,
        graph_config=GraphRAGConfig(
            enable_entity_extraction=True,
            enable_relationship_extraction=True,
            max_hops=2,
            community_detection=True
        )
    )

    # Ingest documents with rich entity relationships
    documents = [
        Document(
            content="Suno AI is a music generation platform that uses machine learning to create original songs from text prompts.",
            title="Suno AI Overview",
            metadata={"type": "platform", "domain": "AI music"}
        ),
        Document(
            content="OpenAI developed GPT-4, which powers many AI applications including music composition and analysis tools.",
            title="OpenAI GPT-4",
            metadata={"type": "platform", "domain": "AI"}
        ),
        Document(
            content="Music generation AI tools like Suno, Udio, and AIVA are revolutionizing content creation for artists and producers.",
            title="AI Music Tools",
            metadata={"type": "tools", "domain": "AI music"}
        )
    ]

    print("Ingesting documents with entity extraction...")
    await r2r.ingest_documents(documents, collection_id="ai-music-graph")

    # Perform graph-based query
    print("\nExecuting GraphRAG query...")
    result = await rag_pipeline.query(
        query="How is Suno AI related to other AI music platforms?",
        collection_id="ai-music-graph",
        limit=5
    )

    print(f"\nAnswer: {result['answer']}\n")
    print(f"Strategy: {result['strategy']}")
    print("\nExtracted entities and relationships will be visualized in the knowledge graph.")


async def example_3_agentic_rag():
    """
    Example 3: Agentic RAG with Multi-Step Reasoning

    Best for: Complex, multi-faceted queries
    """
    print("\n" + "="*60)
    print("Example 3: Agentic RAG with Multi-Step Reasoning")
    print("="*60 + "\n")

    r2r = R2RClient(base_url="http://localhost:7272")

    # Create agentic RAG pipeline
    rag_pipeline = AdvancedRAGPipeline(
        r2r_client=r2r,
        strategy=RAGStrategy.AGENT,
        reranking=RerankingMethod.HYBRID
    )

    # Complex multi-part query
    complex_query = """
    Compare electronic dance music and hip-hop production techniques.
    What are the key differences in BPM, instrumentation, and production workflow?
    Which genre would be better for creating energetic workout music?
    """

    print("Executing agentic RAG with query decomposition...")
    print(f"Query: {complex_query}\n")

    result = await rag_pipeline.query(
        query=complex_query,
        collection_id="music-knowledge",
        limit=10,
        use_query_expansion=True,
        use_reranking=True
    )

    print(f"\nAnswer: {result['answer']}\n")
    print(f"Processed query: {result['processed_query']}")
    print(f"\nThe agent decomposed the query and performed multiple searches.")


async def example_4_rag_to_music():
    """
    Example 4: RAG-Enhanced Music Generation

    Combines knowledge retrieval with music generation
    """
    print("\n" + "="*60)
    print("Example 4: RAG-Enhanced Music Generation")
    print("="*60 + "\n")

    r2r = R2RClient(base_url="http://localhost:7272")

    # Create RAG pipeline
    rag_pipeline = AdvancedRAGPipeline(
        r2r_client=r2r,
        strategy=RAGStrategy.HYBRID
    )

    # Step 1: Use RAG to enhance music prompt
    user_prompt = "Create an energetic workout track"

    print(f"Original prompt: {user_prompt}")
    print("\nEnhancing prompt with RAG...")

    rag_result = await rag_pipeline.query(
        query=f"What are the musical characteristics of {user_prompt}?",
        collection_id="music-knowledge",
        limit=3
    )

    enhanced_prompt = f"{user_prompt}. {rag_result['answer'][:200]}"
    print(f"\nEnhanced prompt: {enhanced_prompt}\n")

    # Step 2: Generate music with enhanced prompt
    # (Uncomment if you have AIMUSIC_API_KEY configured)
    """
    from src.config import load_config
    config = load_config()

    if config.api_key:
        print("Generating music with enhanced prompt...")
        music_client = AIMusicAPIClient(api_key=config.api_key)
        fsm = MusicGenerationFSM(
            api_client=music_client,
            poll_interval=config.poll_interval,
            max_retries=config.max_retries
        )

        request = MusicGenerationRequest(
            custom_mode=False,
            gpt_description_prompt=enhanced_prompt,
            make_instrumental=False,
            mv="chirp-v4",
            voice_gender="female"
        )

        result = fsm.generate_music(request, auto_download=True)
        print(f"\nGenerated {len(result.clips)} music clips!")
        for clip in result.clips:
            print(f"  - {clip.title}: {clip.audio_url}")
    else:
        print("(Music generation skipped - AIMUSIC_API_KEY not configured)")
    """
    print("(Music generation skipped in this example)")


async def example_5_chunking_strategies():
    """
    Example 5: Advanced Chunking Strategies

    Demonstrates different document chunking approaches
    """
    print("\n" + "="*60)
    print("Example 5: Advanced Chunking Strategies")
    print("="*60 + "\n")

    # Sample long document
    long_doc = """
# Music Production Guide

## Introduction
Music production is the process of creating, recording, and refining music.

## Electronic Dance Music (EDM)
EDM is characterized by synthesized sounds, repetitive beats, and high energy.
Typical BPM ranges from 120 to 140. Common sub-genres include house, techno, and trance.

## Hip-Hop Production
Hip-hop relies heavily on sampling and drum machines. The 808 drum machine is iconic.
BPM typically ranges from 80 to 110. Production emphasizes rhythm and vocal delivery.

## Ambient Music
Ambient music creates atmospheric soundscapes with minimal percussion.
Focus is on texture and mood rather than traditional song structure.
    """

    chunker = AdvancedChunker()

    # Strategy 1: Semantic chunking
    print("Strategy 1: Semantic Chunking")
    semantic_chunks = chunker.semantic_chunking(long_doc, max_chunk_size=100)
    print(f"  Created {len(semantic_chunks)} semantic chunks")
    print(f"  First chunk: {semantic_chunks[0][:100]}...\n")

    # Strategy 2: Markdown chunking
    print("Strategy 2: Markdown Structure Chunking")
    markdown_chunks = chunker.markdown_chunking(long_doc)
    print(f"  Created {len(markdown_chunks)} markdown chunks")
    print(f"  First chunk: {markdown_chunks[0][:100]}...\n")

    # Strategy 3: Recursive chunking with overlap
    print("Strategy 3: Recursive Chunking with Overlap")
    recursive_chunks = chunker.recursive_chunking(long_doc, chunk_size=50, chunk_overlap=10)
    print(f"  Created {len(recursive_chunks)} recursive chunks")
    print(f"  Chunk overlap ensures context preservation\n")

    # Ingest with optimal chunking
    r2r = R2RClient(base_url="http://localhost:7272")

    print("Ingesting with semantic chunking...")
    documents = [
        Document(
            content=chunk,
            title=f"Music Production Guide - Part {i+1}",
            metadata={"chunk_strategy": "semantic", "chunk_index": i}
        )
        for i, chunk in enumerate(semantic_chunks)
    ]

    await r2r.ingest_documents(documents, collection_id="chunked-docs")
    print(f"Ingested {len(documents)} semantically chunked documents")


async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("Advanced RAG Examples - RAG Zero to Hero Guide")
    print("="*70)

    examples = [
        ("Hybrid Search", example_1_hybrid_search),
        ("GraphRAG", example_2_graphrag),
        ("Agentic RAG", example_3_agentic_rag),
        ("RAG-Enhanced Music Generation", example_4_rag_to_music),
        ("Chunking Strategies", example_5_chunking_strategies)
    ]

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n⚠️  Example '{name}' failed: {e}")
            print("Make sure R2R service is running and configured correctly.")

        # Pause between examples
        await asyncio.sleep(2)

    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
