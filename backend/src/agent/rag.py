import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

_PDF_PATH = "data/cadquery-readthedocs-io-en-latest.pdf"
_CHROMA_PATH = "data/chroma"
_COLLECTION = "cadquery_docs"
_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
_TOP_K = 6
_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 64

_retriever = None


def build_retriever() -> None:
    global _retriever
    if _retriever is not None:
        return

    embed_model = HuggingFaceEmbedding(model_name=_EMBED_MODEL)
    db = chromadb.PersistentClient(path=_CHROMA_PATH)
    collection = db.get_or_create_collection(_COLLECTION)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_ctx = StorageContext.from_defaults(vector_store=vector_store)

    if collection.count() == 0:
        print("[rag] building index from PDF, this may take a minute...")
        docs = SimpleDirectoryReader(input_files=[_PDF_PATH]).load_data()
        index = VectorStoreIndex.from_documents(
            docs,
            storage_context=storage_ctx,
            embed_model=embed_model,
            transformations=[SentenceSplitter(chunk_size=_CHUNK_SIZE, chunk_overlap=_CHUNK_OVERLAP)],
            show_progress=True,
        )
        print("[rag] index built and persisted.")
    else:
        print("[rag] loading existing index...")
        index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)

    _retriever = index.as_retriever(similarity_top_k=_TOP_K)


def retrieve(query: str) -> str:
    if _retriever is None:
        raise RuntimeError("call build_retriever() before retrieve()")
    nodes = _retriever.retrieve(query)
    return "\n\n---\n\n".join(n.get_content() for n in nodes)