import openai
import logging
import os
from dotenv import load_dotenv

load_dotenv()

class LLMInterface:
    def __init__(self, config):
        self.config = config
        self.model = config['models']['llm_model']
        
        os.environ['OPENAI_API_KEY'] = os.getenv("API_KEY")
        openai.api_key = os.getenv("API_KEY")
        self.client = openai.OpenAI()
        
    
    def generate_answer(self, query: str, context: str) -> str:
        """Generate an answer based on query and context"""
        try:
            prompt = f"""Based on the following context from The Batch articles, please answer the user's question.
            Context:
            {context}
            Question: {query}
            Please provide a comprehensive answer based on the information in the context. If the context doesn't contain enough information to fully answer the question, please indicate that and provide what information is available."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context from The Batch newsletter articles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content
                
        except Exception as e:
            logging.error(f"Error generating LLM response: {e}")
            return f"Error generating response: {str(e)}"
    
    def summarize_article(self, content: str) -> str:
        """Generate a summary of an article"""
        try:
            prompt = f"Please provide a concise summary of the following article:\n\n{content[:2000]}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.5
            )
            return response.choices[0].message.content
                
                
        except Exception as e:
            logging.error(f"Error generating summary: {e}")
            return "Error generating summary"