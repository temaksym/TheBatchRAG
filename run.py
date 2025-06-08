import sys
import argparse
import yaml
import logging
from pathlib import Path

from app.scraper import BatchScraper
from app.multimodal_db import MultimodalDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration file"""
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error("Configuration file not found. Please create config/config.yaml")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)



def scrape_articles(config):
    """Scrape articles from The Batch"""
    logger.info("Starting article scraping...")
    
    scraper = BatchScraper(config)
    articles = scraper.scrape_articles()
    
    if not articles:
        logger.warning("No articles were scraped")
        return []
    
    logger.info(f"Successfully scraped {len(articles)} articles")
    
    # Download images
    logger.info("Downloading images...")
    image_dir = Path("data/images")
    scraper.download_images(articles, str(image_dir))
    
    # Save articles metadata
    import json
    articles_data = []
    for article in articles:
        articles_data.append({
            'title': article.title,
            'content': article.content,
            'url': article.url,
            'images': article.images,
            'metadata': article.metadata
        })
    
    with open("data/processed/articles.json", 'w') as f:
        json.dump(articles_data, f, indent=2)
    
    logger.info("Articles saved to data/processed/articles.json")
    return articles

def build_database(config, articles=None):
    """Build the multimodal database"""
    logger.info("Building multimodal database...")
    
    db = MultimodalDatabase(config)
    
    if articles is None:
        # Load articles from file if not provided
        import json
        articles_file = Path("data/processed/articles.json")
        if not articles_file.exists():
            logger.error("No articles found. Please run scraping first.")
            return
        
        with open(articles_file, 'r') as f:
            articles_data = json.load(f)
        
        # Convert back to Article objects
        from app.scraper import Article
        articles = []
        for data in articles_data:
            article = Article(
                title=data['title'],
                content=data['content'],
                url=data['url'],
                images=data['images'],
                metadata=data['metadata']
            )
            articles.append(article)
    
    # Add articles to database
    db.add_articles(articles)
    
    # Print database stats
    stats = db.get_stats()
    logger.info(f"Database built successfully:")
    logger.info(f"  Total documents: {stats['total_documents']}")
    for doc_type, count in stats['type_breakdown'].items():
        logger.info(f"  {doc_type.title()} documents: {count}")

def launch_ui():
    """Launch the Streamlit UI"""
    import subprocess
    
    logger.info("Launching Streamlit UI...")
    try:
        subprocess.run([
            "streamlit", "run", "app/streamlit_app.py",
            "--server.port=8501",
            "--server.address=localhost"
        ])
    except KeyboardInterrupt:
        logger.info("UI stopped by user")
    except Exception as e:
        logger.error(f"Error launching UI: {e}")


def main():
    parser = argparse.ArgumentParser(description="Multimodal RAG System for The Batch")
    parser.add_argument(
        'command',
        choices=['scrape', 'build-db', 'ui', 'evaluate'],
        help='Command to execute'
    )
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )
    
    args = parser.parse_args()
    
    # Load configuration for other commands
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        logger.info("Run 'python run.py setup' to create initial configuration")
        sys.exit(1)
    
    if args.command == 'scrape':
        scrape_articles(config)
        
    elif args.command == 'build-db':
        build_database(config)
        
    elif args.command == 'ui':
        launch_ui()
        

if __name__ == "__main__":
    main()