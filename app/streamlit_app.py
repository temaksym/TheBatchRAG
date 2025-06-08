import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

from app.multimodal_db import MultimodalDatabase
from app.llm_interface import LLMInterface
from app.scraper import BatchScraper
import yaml
import json
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

@st.cache_resource
def load_config():
    """Load configuration"""
    with open('./config/config.yaml', 'r') as f:
        return yaml.safe_load(f)

@st.cache_resource
def initialize_database():
    """Initialize database connection"""
    config = load_config()
    return MultimodalDatabase(config)

@st.cache_resource
def initialize_llm():
    """Initialize LLM interface"""
    config = load_config()
    return LLMInterface(config)

def display_search_result(result):
    """Display a single search result"""
    with st.container():
        st.write(f"**Similarity Score:** {result['similarity']:.3f}")
        
        if result['type'] == 'text':
            # Display article
            metadata = result['metadata']
            st.write(f"**Title:** {metadata['title']}")
            st.write(f"**URL:** {metadata['url']}")
            
            # Display content preview
            content = result['content']
            if len(content) > 500:
                content = content[:500] + "..."
            st.write(f"**Content Preview:** {content}")
            
            # Display images if available
            if result.get('images'):
                st.write("**Associated Images:**")
                cols = st.columns(min(len(result['images']), 3))
                for i, img_path in enumerate(result['images'][:3]):
                    try:
                        if os.path.exists(img_path):
                            with cols[i]:
                                image = Image.open(img_path)
                                st.image(image, caption=f"Image {i+1}", use_column_width=True)
                    except Exception as e:
                        st.write(f"Error loading image: {e}")
                        
        elif result['type'] == 'image':
            # Display image result
            st.write("**Image Match**")
            try:
                if os.path.exists(result['image_path']):
                    image = Image.open(result['image_path'])
                    st.image(image, caption="Matched Image", use_column_width=True)
                else:
                    st.write("Image file not found")
            except Exception as e:
                st.write(f"Error loading image: {e}")
        
        st.divider()

def main():
    st.set_page_config(
        page_title="The Batch Multimodal RAG",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("'The Batch' Multimodal RAG System")
    
    # Initialize components
    try:
        db = initialize_database()
        llm = initialize_llm()
    except Exception as e:
        st.error(f"Error initializing system: {e}")
        st.stop()
    
    # Sidebar 
    with st.sidebar:
        
        # Search settings
        st.subheader("Search Settings")
        max_results = st.slider("Max Results", 1, 10, 5)
        include_images = st.checkbox("Include Image Results", True)
        use_llm_generation = st.checkbox("Use LLM for Answer Generation", True)
        
        st.subheader("Database Stats")
        try:
            stats = db.get_stats()
            st.metric("Total Documents", stats['total_documents'])
            
            for doc_type, count in stats['type_breakdown'].items():
                st.metric(f"{doc_type.title()} Documents", count)
        except Exception as e:
            st.error(f"Error loading stats: {e}")

    
    # Main search interface
    st.header("Search Interface")
    
    query = st.text_input(
        "Enter your query:",
        placeholder="e.g., machine learning in healthcare, computer vision applications..."
    )
    
    if query:
        with st.spinner("Searching..."):
            try:
                # Perform search
                results = db.search(
                    query=query,
                    n_results=max_results,
                    include_images=include_images
                )
                
                if results:
                    # Generate LLM response if enabled
                    if use_llm_generation:
                        st.subheader("AI-Generated Answer")
                        try:
                            # Prepare context from search results
                            context = []
                            for result in results[:3]:  # Use top 3 results
                                if result['type'] == 'text':
                                    context.append(f"Title: {result['metadata']['title']}")
                                    context.append(f"Content: {result['content'][:1000]}")
                            
                            context_text = "\n\n".join(context)
                            answer = llm.generate_answer(query, context_text)
                            st.write(answer)
                            
                        except Exception as e:
                            st.error(f"Error generating answer: {e}")
                    
                    # Display search results
                    st.subheader(f"Search Results ({len(results)} found)")
                    
                    for i, result in enumerate(results):
                        with st.expander(f"Result {i+1} - Similarity: {result['similarity']:.3f}"):
                            display_search_result(result)
                            
                else:
                    st.warning("No results found for your query.")
                    
            except Exception as e:
                st.error(f"Error during search: {e}")
    

if __name__ == "__main__":
    main()