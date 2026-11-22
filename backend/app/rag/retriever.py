from pathlib import Path
from app.rag.chunker import chunker
from app.rag.vector_store import vector_store
from app.observability.logger import get_logger

logger = get_logger(__name__)

INDEXABLE_EXTENSIONS = {".py", ".js", ".ts", ".tsx"}
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build"}


class Retriever:
    def index_repo(self, repo: str, repo_path: str | Path) -> int:
        """Walk a local repo directory and index every code file."""
        repo_path = Path(repo_path)
        total_chunks = 0

        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in INDEXABLE_EXTENSIONS:
                continue
            if any(part in SKIP_DIRS for part in file_path.parts):
                continue

            chunks = chunker.chunk_file(file_path)
            if chunks:
                total_chunks += vector_store.index_chunks(repo, chunks)

        logger.info("repo_indexed", repo=repo, total_chunks=total_chunks)
        return total_chunks

    def search(self, repo: str, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search — used by CodebaseExplorer agent."""
        return vector_store.search(repo, query, top_k=top_k)


retriever = Retriever()