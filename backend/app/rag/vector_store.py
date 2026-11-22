import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import get_settings
from app.rag.chunker import CodeChunk
from app.rag.embedder import embedder
from app.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _collection_name(self, repo: str) -> str:
        return f"repo_{repo.replace('/', '_').replace('-', '_')}"

    def get_or_create(self, repo: str):
        return self.client.get_or_create_collection(name=self._collection_name(repo))

    def index_chunks(self, repo: str, chunks: list[CodeChunk]) -> int:
        if not chunks:
            return 0

        collection = self.get_or_create(repo)
        texts = [c.content for c in chunks]
        embeddings = embedder.embed(texts)

        ids = [f"{c.file_path}:{c.start_line}-{c.end_line}" for c in chunks]
        metadatas = [{
            "file_path": c.file_path,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "chunk_type": c.chunk_type,
        } for c in chunks]

        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        logger.info("indexed_chunks", repo=repo, count=len(chunks))
        return len(chunks)

    def search(self, repo: str, query: str, top_k: int = 5) -> list[dict]:
        collection = self.get_or_create(repo)
        query_embedding = embedder.embed_one(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        return [
            {
                "content": doc,
                "file_path": meta["file_path"],
                "start_line": meta["start_line"],
                "end_line": meta["end_line"],
                "distance": dist,
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]


vector_store = VectorStore()