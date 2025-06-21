import asyncio
import sys
import os
sys.path.append('.')

from app.core.ingest.processors import DocumentProcessor
from app.db.connection import async_session
from app.db.models import Document, Embedding
from sqlalchemy import text
from pathlib import Path
import time

async def ingest_nasa_document():
    # Wait for DB to be ready
    await asyncio.sleep(3)
    
    # Process the NASA document
    processor = DocumentProcessor()
    file_path = 'uploads/NASA_Open_Source_Agreement_1.3.pdf'
    
    if not os.path.exists(file_path):
        print(f'File not found: {file_path}')
        return
    
    print(f'Processing {file_path}...')
    result = processor.process_document(file_path)
    
    if not result['success']:
        print(f'Failed to process document: {result.get("error", "Unknown error")}')
        return
    
    print(f'Successfully processed document: {len(result["chunks"])} chunks created')
    
    # Save to database
    async with async_session() as session:
        # Check if document already exists
        existing = await session.execute(
            text("SELECT id FROM documents WHERE filename = :filename"),
            {"filename": "NASA_Open_Source_Agreement_1.3.pdf"}
        )
        if existing.fetchone():
            print("Document already exists in database")
            return
        
        # Create document record
        document = Document(
            filename='NASA_Open_Source_Agreement_1.3.pdf',
            file_type='pdf',
            file_size=45*1024,  # Approximate size
            original_text=result['cleaned_text'],
            processed_chunks=len(result['chunks']),
            metadata_={
                'processing_stats': result['processing_stats'],
                'document_summary': result['document_summary']
            }
        )
        
        session.add(document)
        await session.flush()  # Get the document ID
        
        # Create embedding records for each chunk
        for chunk in result['chunks']:
            embedding = Embedding(
                document_id=document.id,
                chunk_id=chunk['chunk_id'],
                chunk_text=chunk['text'],
                chunk_type=chunk.get('chunk_type', 'paragraph'),
                start_char=chunk['start_char'],
                end_char=chunk['end_char'],
                metadata_=chunk.get('metadata', {})
            )
            session.add(embedding)
        
        await session.commit()
        print(f'Successfully saved document to database with ID: {document.id}')
        print(f'Created {len(result["chunks"])} embedding records')

if __name__ == "__main__":
    asyncio.run(ingest_nasa_document()) 