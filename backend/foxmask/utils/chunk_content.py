from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def chunk_markdown_content(md_content, metadata=None, chunk_size=1000, chunk_overlap=200):
    # Create a Document object with markdown content and metadata
    if metadata is None:
        metadata = {}
    document = Document(page_content=md_content, metadata=metadata)
    
    # Split by markdown headers
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    header_splits = markdown_splitter.split_text(document.page_content)
    
    # Preserve original metadata and combine with header metadata
    for split in header_splits:
        split.metadata = {**document.metadata, **split.metadata}
    
    # Further split large chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    final_chunks = []
    for split in header_splits:
        chunks = text_splitter.split_documents([split])
        final_chunks.extend([c.page_content for c in chunks])

    indexed_chunks = [{"index": i, "content": chunk} for i, chunk in enumerate(final_chunks, start=1)]
    return indexed_chunks

# Example usage
if __name__ == "__main__":
    sample_md_content = """
# Main Title
This is the main content under the first header.

## Subheader 1
Some detailed information here.

### Sub-subheader
More specific details.

## Subheader 2
Another section with content.
"""
    sample_metadata = {"source": "example", "author": "John Doe", "date": "2025-09-17"}
    
    chunks = chunk_markdown_content(sample_md_content, sample_metadata)
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i + 1}:")
        print(f"Metadata: {chunk.metadata}")
        print(f"Content: {chunk.page_content[:200]}...")