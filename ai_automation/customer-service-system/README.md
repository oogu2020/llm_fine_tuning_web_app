# Customer Support Email Agent

An intelligent email support system built with LangGraph and Python 3.12. This agent automatically processes customer support emails, classifies intent, drafts responses using a knowledge base, and escalates to humans when needed.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Ingest    │────▶│  Classify   │────▶│   Draft     │
│   Email     │     │   Intent    │     │  Response   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                        ┌──────────────────────┼──────────────────────┐
                        ▼                      ▼                      ▼
                ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                │    Send     │      │   Review    │      │   Escalate  │
                │  Response   │      │  (Human)    │      │   to Human  │
                └─────────────┘      └─────────────┘      └─────────────┘
```

## Features

- **Email Ingestion**: Connects to IMAP/SMTP for reading and sending emails
- **Intent Classification**: Uses LLM to categorize customer requests
- **Knowledge Base**: ChromaDB vector store for retrieving relevant documentation
- **Response Drafting**: AI-powered response generation with context
- **Quality Review**: Automated review before sending
- **Human Escalation**: Smart routing for complex issues

## Quick Start

### Prerequisites

- Python 3.12+
- Anthropic API key (or OpenAI)
- Email account with IMAP/SMTP access

### Installation

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and email settings
```

### Configuration

Create a `.env` file with:

```env
# LLM Configuration
ANTHROPIC_API_KEY=your_api_key_here
LLM_MODEL=claude-3-5-sonnet-20241022

# Email Configuration
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=support@yourcompany.com
EMAIL_PASSWORD=your_app_password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Vector Store
CHROMA_PERSIST_DIR=./data/chroma

# App Settings
LOG_LEVEL=INFO
DEBUG=false
```

### Running the Agent

```bash
# Start the API server
uvicorn src.api.main:app --reload

# Or run CLI mode
python -m src.cli
```

## Project Structure

```
src/
├── core/           # Configuration, logging, exceptions
├── agent/          # LangGraph workflow and nodes
├── services/       # Business logic (email, KB, LLM)
├── api/            # FastAPI endpoints
├── schemas/        # Pydantic data models
├── prompts/        # LLM prompt templates
├── utils/          # Helper functions
└── knowledge_base/ # Vector store and documents

data/               # Runtime data storage
├── emails/         # Processed emails
└── logs/           # Application logs
```

## Development

```bash
# Run tests
pytest

# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

## License

MIT
