import time
from src.rag.embedding_service import EmbeddingService

def test_rag():
    print("⏳ Initializing RAG Engine (First run downloads the model)...")
    start = time.time()

    rag = EmbeddingService()

    print(f"✅ Model Loaded in {time.time() - start:.2f}s")

    text1 = "Sailesh is building Identra."
    text2 = "Identra is a privacy-first AI project."
    text3 = "I like eating pizza."

    print("\n🧠 Generating Vectors...")
    v1 = rag.generate_embedding(text1)
    v2 = rag.generate_embedding(text2)
    v3 = rag.generate_embedding(text3)

    # Check similarity
    sim_1_2 = rag.calculate_similarity(v1, v2) # Should be High
    sim_1_3 = rag.calculate_similarity(v1, v3) # Should be Low

    print("\n📊 Similarity Analysis:")
    print(f"1 vs 2 (Identra Context): {sim_1_2:.4f} (Expected > 0.4)")
    print(f"1 vs 3 (Pizza Context):   {sim_1_3:.4f} (Expected < 0.2)")

if __name__ == "__main__":
    test_rag()