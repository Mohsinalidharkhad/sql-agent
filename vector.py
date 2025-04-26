import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import ast
import re
import numpy as np
from supabase import create_client, Client
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.schema import BaseRetriever
from langchain.schema.document import Document
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from pydantic import Field

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    openai_api_key=os.environ.get("OPENAI_API_KEY")
)

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# Create index if it doesn't exist
index_name = "restaurant-db"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,  # dimension for text-embedding-3-small
        metric="cosine"
    )

index = pc.Index(index_name)
vector_store = PineconeVectorStore(embedding=embeddings, index=index)


def get_table_columns() -> List[Dict]:
    """
    Fetch all tables and their text-based columns from Supabase.
    Returns a list of table configurations.
    """
    try:
        # Query to get all tables and their columns
        query = """
        SELECT 
            table_name,
            column_name,
            data_type
        FROM 
            information_schema.columns
        WHERE 
            table_schema = 'public'
            AND data_type IN ('character varying', 'text', 'varchar', 'char')
        ORDER BY 
            table_name, column_name
        """
        
        result = supabase.rpc('execute_sql', {'query': query}).execute()
        
        # Process results into table configs
        table_configs = []
        for row in result.data:
            table_configs.append({
                'table': row['table_name'],
                'column': row['column_name']
            })
        
        print(f"Found {len(table_configs)} text columns across all tables")
        return table_configs
        
    except Exception as e:
        print(f"Error fetching table information: {str(e)}")
        return []


def fetch_column_content() -> List[Dict]:
    """
    Fetch all text content from the identified columns and return as a list of dicts
    containing both the content and its metadata.
    Returns a list of dicts with text content and metadata about its source.
    """
    try:
        table_configs = get_table_columns()
        all_content = []
        
        for config in table_configs:
            # Construct and execute query for each column
            query = f"""
            SELECT DISTINCT {config['column']}
            FROM {config['table']}
            WHERE {config['column']} IS NOT NULL
            """
            
            result = supabase.rpc('execute_sql', {'query': query}).execute()
            
            # Extract content from the results and add metadata
            for row in result.data:
                if row[config['column']]:  # Check if the value is not None or empty
                    # Clean the text: remove extra whitespace and numeric-only strings
                    cleaned_text = re.sub(r'\s+', ' ', str(row[config['column']])).strip()
                    if cleaned_text and not cleaned_text.isnumeric():
                        content_with_metadata = {
                            'text': cleaned_text,
                            'metadata': {
                                'table_name': config['table'],
                                'column_name': config['column']
                            }
                        }
                        all_content.append(content_with_metadata)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_content = []
        for item in all_content:
            if item['text'] not in seen:
                seen.add(item['text'])
                unique_content.append(item)
                
        print(f"Found {len(unique_content)} unique text entries across all columns")
        return unique_content
        
    except Exception as e:
        print(f"Error fetching column content: {str(e)}")
        return []


def add_to_vector_store(content_list: List[Dict]):
    texts = [item['text'] for item in content_list]
    metadatas = [item['metadata'] for item in content_list]
    
    _ = vector_store.add_texts(texts=texts, metadatas=metadatas)
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 20},
        search_type="similarity"
    )
    description = (
        "Use to look up values to filter on. Input is an approximate spelling "
        "of the proper noun, output is valid proper nouns with their source information. "
        "Use the noun most similar to the search."
    )
    retriever_tool = create_retriever_tool(
        retriever,
        name="search_proper_nouns",
        description=description,
    )
    return retriever


# Example usage
if __name__ == "__main__":
    try:
        content = fetch_column_content()
        print("\nSample of content found (first 10 entries):")
        for item in content[:10]:
            print(f"- {item['text']} (Present in '{item['metadata']['column_name']}' column in '{item['metadata']['table_name']}' table)")
        
        retriever = add_to_vector_store(content)
        print("\nTesting search with 'paneer':")
        # Get results directly from retriever
        results = retriever.get_relevant_documents("paneer")
        for doc in results:
            print(f"\n- {doc.page_content}")
            print(f"  (Present in '{doc.metadata['column_name']}' column in '{doc.metadata['table_name']}' table)")
        
    except Exception as e:
        print(f"Error: {e}") 