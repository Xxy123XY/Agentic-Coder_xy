from sentence_transformers import SentenceTransformer
from functools import lru_cache
from app.config import get_settings
from app.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    logger.info("loading_embedding_model", model=settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


class Embedder:
    @property
    def model(self) -> SentenceTransformer:
        return _load_model()

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


embedder = Embedder()