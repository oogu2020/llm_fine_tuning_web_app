# Customer Support Email Agent

An intelligent email support system built with LangGraph and Python 3.12. This agent automatically processes customer support emails, classifies intent, retrieves relevant documentation, drafts responses, and handles human escalation when needed.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Ingest    │────▶│  Classify   │────▶│  Retrieve   │
│   Email     │     │   Intent    │     │     KB      │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                        ┌──────────────────────┼──────────────────────┐
                        ▼                      ▼                      ▼
                ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                │    Send     │      │   Review    │      │   Escalate  │
                │  Response   │◀─────│  Response   │      │   to Human  │
                └─────────────┘      └──────┬──────┘      └─────────────┘
                                            │
                                     ┌──────┴──────┐
                                     ▼             ▼
                                ┌─────────┐  ┌──────────┐
                                │ Approve │  │  Revise  │
                                └─────────┘  └──────────┘
```

## Features

- **Email Ingestion**: Connects to IMAP/SMTP for reading and sending emails
- **Intent Classification**: Uses LLM to categorize customer requests
- **Knowledge Base**: ChromaDB vector store for retrieving relevant documentation
- **Response Drafting**: AI-powered response generation with citations
- **Quality Review**: Automated review with retry logic
- **Human Escalation**: Smart routing for complex issues
- **API Server**: FastAPI with REST endpoints
- **CLI Tool**: Command-line interface for manual operations

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

Create a `.env` file:

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
```

### Index Knowledge Base

```bash
# Index documentation into ChromaDB
python -m src.cli index-docs --dir ./src/knowledge_base/documents
```

### Run the Agent

#### Option 1: API Server

```bash
# Start the API server
python -m src.cli serve

# Or with uvicorn directly
uvicorn src.api.main:app --reload
```

Access the API docs at `http://localhost:8000/docs`

#### Option 2: CLI

```bash
# Fetch and process unread emails
python -m src.cli fetch

# Process a single email manually
python -m src.cli process

# Search knowledge base
python -m src.cli search-kb
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/emails/process` | Process a new email |
| POST | `/api/v1/emails/fetch` | Fetch unread from IMAP |
| GET | `/api/v1/emails/` | List processed emails |
| GET | `/api/v1/emails/{id}` | Get email by ID |
| POST | `/api/v1/emails/{id}/escalate` | Manual escalation |
| POST | `/api/v1/emails/{id}/send` | Send pending response |
| GET | `/health` | Health check |

### Example: Process Email

```bash
curl -X POST http://localhost:8000/api/v1/emails/process \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "How do I reset my password?",
    "body": "I forgot my password and can't log in.",
    "sender": "customer@example.com"
  }'
```

## Project Structure

```
src/
├── agent/              # LangGraph workflow
│   └── graph.py        # Full workflow implementation
├── api/                # FastAPI application
│   ├── main.py         # API entry point
│   └── routes/         # API endpoints
├── core/               # Configuration, logging, exceptions
├── knowledge_base/     # Vector store and documents
│   └── documents/      # Knowledge base content
├── prompts/            # LLM prompt templates
├── schemas/            # Pydantic data models
├── services/           # Business logic
│   ├── llm_service.py  # LLM client
│   ├── email_service.py # IMAP/SMTP operations
│   └── kb_service.py   # Knowledge base operations
└── utils/              # Helper functions
```

## How It Works

### 1. Ingest Node
- Receives incoming email
- Extracts structured data (sender, subject, body)
- Cleans body text (removes signatures, quotes)

### 2. Classify Node
- Uses LLM to classify intent (billing, technical, general inquiry, etc.)
- Assigns priority (low, medium, high, critical)
- Determines if human escalation is needed
- Extracts key points from the email

### 3. Retrieve Node
- Builds search query from email content
- Queries ChromaDB vector store
- Returns top-k relevant documents

### 4. Draft Node
- Uses LLM with retrieved context to draft response
- Includes citations to knowledge base
- Adapts tone based on intent (apologetic for complaints, etc.)

### 5. Review Node
- LLM reviews drafted response for accuracy
- Checks against knowledge base
- Returns approval decision or feedback for revision
- Implements retry logic (max 5 iterations)

### 6. Send/Escalate Nodes
- Sends approved responses via SMTP
- Or escalates to human agents

## Flow Control

The graph uses conditional routing:

**After Classification:**
- Routes to `retrieve` if confidence is high
- Routes to `escalate` if confidence is low or intent requires human

**After Review:**
- Routes to `send` if approved
- Routes to `draft` (with feedback) if needs revision
- Routes to `escalate` if max iterations reached

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

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `LLM_PROVIDER` | LLM provider (anthropic/openai) | anthropic |
| `LLM_MODEL` | Model name | claude-3-5-sonnet-20241022 |
| `EMAIL_HOST` | IMAP server | imap.gmail.com |
| `SMTP_HOST` | SMTP server | smtp.gmail.com |
| `AGENT_AUTO_SEND` | Auto-send responses | false |
| `AGENT_MAX_ITERATIONS` | Max draft revisions | 5 |

## Troubleshooting

### Gmail Authentication

For Gmail, use an App Password:
1. Enable 2FA on Google Account
2. Go to Security > App Passwords
3. Generate new app password for "Mail"
4. Use that password in `.env`

### ChromaDB Issues

If you get embedding errors:
```bash
# The sentence-transformers model will download on first use
# Ensure you have internet connectivity for initial download
```

### LLM Errors

Check API key and model availability:
```bash
# Test LLM connection
python -c "from src.services.llm_service import get_llm_service; print(get_llm_service().get_client())"
```

## License

MIT
