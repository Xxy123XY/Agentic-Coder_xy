from pathlib import Path
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser
from dataclasses import dataclass


@dataclass
class CodeChunk:
    file_path: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str  # "function", "class", "module"


LANGUAGE_MAP = {
    ".py": Language(tree_sitter_python.language()),
    ".js": Language(tree_sitter_javascript.language()),
    ".ts": Language(tree_sitter_typescript.language_typescript()),
    ".tsx": Language(tree_sitter_typescript.language_tsx()),
}

CHUNK_NODE_TYPES = {
    "function_definition",
    "function_declaration",
    "class_definition",
    "class_declaration",
    "method_definition",
}


class CodeChunker:
    def chunk_file(self, file_path: str | Path) -> list[CodeChunk]:
        path = Path(file_path)
        ext = path.suffix

        if ext not in LANGUAGE_MAP:
            return []

        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            return []

        parser = Parser(LANGUAGE_MAP[ext])
        tree = parser.parse(source.encode("utf-8"))
        chunks: list[CodeChunk] = []

        self._walk(tree.root_node, source, str(path), chunks)
        return chunks

    def _walk(self, node, source: str, file_path: str, chunks: list[CodeChunk]):
        if node.type in CHUNK_NODE_TYPES:
            chunks.append(CodeChunk(
                file_path=file_path,
                content=source[node.start_byte:node.end_byte],
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                chunk_type=node.type,
            ))
            return  # skip nested functions to avoid duplicates

        for child in node.children:
            self._walk(child, source, file_path, chunks)


chunker = CodeChunker()