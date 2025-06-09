# The Batch Multimodal RAG System

A Retrieval-Augmented Generation (RAG) system for "The Batch" newsletter by DeepLearning.AI. This project scrapes articles and images, builds a multimodal vector database, and provides a Streamlit-powered UI for semantic search and LLM-based question answering.

Demo of working prototype is here: https://youtu.be/xLqsQQZvZhY

---

## Features

- **Automated Scraping**: Collects articles and images from The Batch, including paginated and "Load More" sections.
- **Multimodal Database**: Stores both text and image embeddings using ChromaDB, Sentence Transformers, and CLIP.
- **Semantic Search**: Retrieve relevant articles and images for any query.
- **LLM Integration**: Uses OpenAI GPT models for answer generation and summarization.
- **Streamlit UI**: User-friendly interface for searching, exploring, and visualizing results.
- **Configurable**: All settings in `config/config.yaml`.

---

## Project Structure

```
TheBatchRAG/
├── app/
│   ├── scraper.py
│   ├── multimodal_db.py
│   ├── llm_interface.py
│   └── streamlit_app.py
├── config/
│   └── config.yaml
├── data/
│   ├── images/
│   ├── processed/
│   └── chroma_db/
├── requirements.txt
├── run.py
└── README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/temaksym/TheBatchRAG.git
cd TheBatchRAG
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv my_venv
source my_venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

- Create a `.env` file in the root directory:
  ```
  API_KEY=your_openai_api_key
  ```
- Or add your key to `config/config.yaml` under an `api` section (not recommended for production).

### 5. Configure settings

Edit `config/config.yaml` to adjust scraping, database, and UI settings as needed.

---

## Usage

### Scrape Articles

```bash
python run.py scrape
```

### Build the Multimodal Database

```bash
python run.py build-db
```

### Launch the Streamlit UI

```bash
python run.py ui
```

The UI will be available at [http://localhost:8501](http://localhost:8501).

---

## Customization

- **Scraping**: Adjust selectors or categories in `app/scraper.py` if the website structure changes.
- **Models**: Change embedding or LLM models in `config/config.yaml`.
- **UI**: Modify `app/streamlit_app.py` for custom interface features.

---

## Troubleshooting

- **API Key Errors**: Ensure your `.env` file is present and correct.
- **Selenium/Browser Issues**: Make sure Firefox is installed for scraping "Load More" sections.
- **Streamlit Watcher Errors**: These can often be ignored if the UI works.

---

## License

MIT License
