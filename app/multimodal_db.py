import chromadb
import json
from typing import List
from sentence_transformers import SentenceTransformer
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import logging

class MultimodalDatabase:
    def __init__(self, config):
        self.config = config
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=config['database']['persist_directory']
        )
        
        # Initialize embedding models
        self.text_model = SentenceTransformer(config['models']['text_embedding'])
        
        # Initialize CLIP for image embeddings using Hugging Face
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model.to(self.device)
        except Exception as e:
            logging.error(f"Failed to load CLIP model: {e}")
            self.clip_model = None
            self.clip_processor = None
        
        # Get embedding dimensions
        self.text_dim = self.text_model.get_sentence_embedding_dimension()
        self.image_dim = self.clip_model.config.projection_dim if self.clip_model else 512
        
        # Create separate collections for text and images
        self.text_collection = self.client.get_or_create_collection(
            name=f"{config['database']['collection_name']}_text",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.image_collection = self.client.get_or_create_collection(
            name=f"{config['database']['collection_name']}_images", 
            metadata={"hnsw:space": "cosine"}
        )
        
    def add_articles(self, articles: List):
        """Add articles to the database"""
        text_documents = []
        text_metadatas = []
        text_ids = []
        text_embeddings = []
        
        image_documents = []
        image_metadatas = []
        image_ids = []
        image_embeddings = []
        
        for i, article in enumerate(articles):
            # Skip articles without title or content
            if not hasattr(article, 'title') or not hasattr(article, 'content'):
                continue
                
            # Create document text
            doc_text = f"{article.title}\n\n{article.content}"
            
            # Create metadata
            metadata = {
                'title': article.title,
                'url': getattr(article, 'url', ''),
                'images': json.dumps(getattr(article, 'images', [])),
                'metadata': json.dumps(getattr(article, 'metadata', {})),
                'type': 'text'
            }
            
            # Generate text embedding
            text_embedding = self.text_model.encode(doc_text)
            
            text_documents.append(doc_text)
            text_metadatas.append(metadata)
            text_ids.append(f"article_{i}")
            text_embeddings.append(text_embedding.tolist())
            
            # Add image embeddings if images exist
            images = getattr(article, 'images', [])
            for j, image_path in enumerate(images):
                try:
                    image_embedding = self._encode_image(image_path)
                    if image_embedding is not None:
                        image_metadata = metadata.copy()
                        image_metadata.update({
                            'type': 'image',
                            'image_path': image_path,
                            'parent_article': f"article_{i}"
                        })
                        
                        image_documents.append(f"Image from: {article.title}")
                        image_metadatas.append(image_metadata)
                        image_ids.append(f"image_{i}_{j}")
                        image_embeddings.append(image_embedding.tolist())
                        
                except Exception as e:
                    logging.error(f"Error processing image {image_path}: {e}")
        
        # Add to separate collections
        if text_documents:
            self.text_collection.add(
                documents=text_documents,
                metadatas=text_metadatas,
                ids=text_ids,
                embeddings=text_embeddings
            )
            logging.info(f"Added {len(text_documents)} text documents")
        
        if image_documents:
            self.image_collection.add(
                documents=image_documents,
                metadatas=image_metadatas,
                ids=image_ids,
                embeddings=image_embeddings
            )
            logging.info(f"Added {len(image_documents)} image documents")
    
    def _encode_image(self, image_path: str):
        """Encode image using CLIP"""
        if self.clip_model is None or self.clip_processor is None:
            logging.warning("CLIP model not available, skipping image encoding")
            return None
            
        try:
            image = Image.open(image_path).convert('RGB')
            inputs = self.clip_processor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
            return image_features.cpu().numpy()[0]
            
        except Exception as e:
            logging.error(f"Error encoding image {image_path}: {e}")
            return None
     
    def search(self, query: str, n_results: int = 5, include_images: bool = True):
        """Search for relevant content"""
        # Generate query embedding for text search
        query_embedding = self.text_model.encode(query)
        
        # Search in text collection
        text_results = self.text_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        processed_results = []
        
        # Process text results
        for doc, metadata, distance in zip(
            text_results['documents'][0],
            text_results['metadatas'][0], 
            text_results['distances'][0]
        ):
            processed_results.append({
                'type': 'text',
                'content': doc,
                'metadata': metadata,
                'similarity': 1 - distance,
                'images': json.loads(metadata['images']) if include_images else []
            })
        
        # Search in image collection if requested and CLIP is available
        if include_images and self.clip_model is not None:
            try:
                # Generate image query embedding using CLIP text encoder
                text_inputs = self.clip_processor(text=[query], return_tensors="pt", padding=True).to(self.device)
                with torch.no_grad():
                    text_features = self.clip_model.get_text_features(**text_inputs)
                    text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                image_query_embedding = text_features.cpu().numpy()[0]
                
                image_results = self.image_collection.query(
                    query_embeddings=[image_query_embedding.tolist()],
                    n_results=n_results // 2,  # Limit image results
                    include=['documents', 'metadatas', 'distances']
                )
                
                # Process image results
                for doc, metadata, distance in zip(
                    image_results['documents'][0],
                    image_results['metadatas'][0],
                    image_results['distances'][0]
                ):
                    processed_results.append({
                        'type': 'image',
                        'content': doc,
                        'metadata': metadata,
                        'similarity': 1 - distance,
                        'image_path': metadata['image_path']
                    })
                    
            except Exception as e:
                logging.error(f"Error searching images: {e}")
        
        # Sort by similarity and return top results
        processed_results.sort(key=lambda x: x['similarity'], reverse=True)
        return processed_results[:n_results]
    
    def get_stats(self):
        """Get database statistics"""
        text_count = self.text_collection.count()
        image_count = self.image_collection.count()
        
        return {
            'total_documents': text_count + image_count,
            'text_documents': text_count,
            'image_documents': image_count,
            'type_breakdown': {
                'text': text_count,
                'image': image_count
            }
        }