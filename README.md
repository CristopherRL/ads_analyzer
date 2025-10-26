# Digital Marketing Analysis Agent

AI-powered backend for Facebook Ads performance analysis using LangChain and FastAPI.

## 🚀 Overview

This application provides a conversational AI agent that helps analyze Facebook advertising campaign performance. The agent can:

- List available Facebook advertising accounts
- Analyze campaign performance data with intelligent caching
- Provide insights and recommendations based on real data
- Maintain conversation context across sessions

## 🏗️ Architecture

- **Backend:** FastAPI
- **AI Orchestrator:** LangChain
- **LLM:** Azure OpenAI (GPT-4o)
- **Database:** Azure Database for PostgreSQL
- **Secrets Management:** Azure Key Vault
- **Deployment:** Azure Container Apps

## 📁 Project Structure

```
.
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── config.py
├── main.py
├── pytest.ini
├── requirements.txt
├── src
│   ├── __init__.py
│   ├── agent
│   │   ├── __init__.py
│   │   ├── agent_executor.py
│   │   └── memory.py
│   ├── database.py
│   ├── logging_config.py
│   ├── models.py
│   ├── prompts
│   │   └── default_system_prompt.txt
│   ├── schemas.py
│   └── tools
│       ├── __init__.py
│       └── facebook_tools.py
└── tests
    ├── __init__.py
    └── test_main.py
```

## 🛠️ Local Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database (local or Azure)
- Azure OpenAI service
- Facebook Developer account with Ads API access

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd <repository-name>

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy example file
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# === Database Configuration ===
DATABASE_CONNECTION_STRING=postgresql://username:password@host:port/database_name

# === Facebook API Credentials ===
FB_APP_ID=your_facebook_app_id
FB_APP_SECRET=your_facebook_app_secret
FB_ACCESS_TOKEN=your_facebook_access_token
FB_AD_ACCOUNT_ID=act_your_ad_account_id

# === Azure OpenAI Configuration ===
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_INFERENCE_CREDENTIAL=

# === Application Configuration ===
DEBUG=True

# === LangChain Configuration (recomendations) ===
MEMORY_TEMPERATURE=0.1
MEMORY_MAX_TOKEN_LIMIT=2000
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=2000
AGENT_MAX_ITERATIONS=5
CACHE_EXPIRATION_HOURS=1

# === Logging Configuration ===
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
LOG_FORMAT='%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# === Prompt Configuration ===
SYSTEM_PROMPT_SOURCE=default
DEFAULT_PROMPT_FILE=src/prompts/default_system_prompt.txt
```

### 3. Database Setup

Create the database tables by running the following Python script from the root of the project:

```python
# Run this Python script to create tables
python -c "
from src.database import create_tables
create_tables()
print('Database tables created successfully!')
"
```

### 4. Run the Application

```bash
# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API:** http://127.0.0.1:8000
- **Interactive Docs:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

## 📚 API Usage

### Health Check

```bash
# Check service health
curl http://127.0.0.1:8000/health

# Check database health
curl http://127.0.0.1:8000/health/db
```

### Chat with Agent

#### Start a Conversation

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "cristopher@example.com",
    "message": "Hola, quiero analizar mis campañas de Facebook"
  }'
```

**Response:**
```json
{
  "response": "¡Hola Cristopher! 👋 Soy tu experto en Marketing Digital...",
  "session_id": "20241201_143022_cristopher_at_example_com",
  "user_id": "cristopher@example.com"
}
```

#### Continue Conversation

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "cristopher@example.com",
    "message": "Quiero analizar la cuenta act_123456789",
    "session_id": "20241201_143022_cristopher_at_example_com"
  }'
```

### Authentication

#### Login (Simple Email Verification)

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cristopher@example.com"
  }'
```

#### Verify User

```bash
curl "http://127.0.0.1:8000/auth/verify/cristopher@example.com"
```

### Session Management

#### Get Session Info

```bash
curl "http://127.0.0.1:8000/chat/session/20241201_143022_cristopher_at_example_com"
```

#### Clear Session

```bash
curl -X DELETE "http://127.0.0.1:8000/chat/session/20241201_143022_cristopher_at_example_com"
```

## 🧪 Testing

### Using FastAPI Interactive Docs

1. Open http://127.0.0.1:8000/docs
2. Click on any endpoint to expand it
3. Click "Try it out"
4. Fill in the request parameters
5. Click "Execute"

### Using curl

```bash
# Test health endpoint
curl http://127.0.0.1:8000/health

# Test chat endpoint
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test@example.com",
    "message": "Hello, I want to analyze my Facebook campaigns"
  }'
```

### Using Python requests

```python
import requests

# Test chat endpoint
response = requests.post(
    "http://127.0.0.1:8000/chat",
    json={
        "user_id": "test@example.com",
        "message": "Hello, I want to analyze my Facebook campaigns"
    }
)

print(response.json())
```

## 📊 Database Schema

### Tables

- **`users`**: Stores user information.
- **`facebook_accounts`**: Manages Facebook advertising accounts.
- **`user_facebook_accounts`**: Many-to-many relationship between users and Facebook accounts.
- **`api_cache`**: Caches responses from the Facebook API.
- **`conversation_history`**: Records the chat history for each user session.
- **`prompt_versions`**: Manages different versions of system prompts for the agent.
- **`campaign_performance_data`**: Stores historical campaign performance metrics.
- **`model_mappings`**: Maps assigned model names to generic model names for cost tracking.
- **`model_pricing`**: Stores pricing information for different AI models.
- **`analysis_results`**: Stores the results of analyses generated by the AI.


## 🔧 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode |
| `MEMORY_TEMPERATURE` | `0.1` | Temperature for memory summarization |
| `AGENT_TEMPERATURE` | `0.7` | Temperature for agent responses |
| `CACHE_EXPIRATION_HOURS` | `1` | API cache expiration time |
| `SYSTEM_PROMPT_SOURCE` | `database` | Prompt source: `default` or `database` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FILE` | `logs/app.log` | Path to the log file. |

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check `DATABASE_CONNECTION_STRING` format
   - Verify database is running and accessible

2. **Azure OpenAI Error**
   - Verify `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`
   - Check deployment name matches your Azure setup

3. **Facebook API Error**
   - Verify Facebook credentials and permissions
   - Check ad account ID format (`act_123456789`)

### Logs

The application will create a `logs` directory if it doesn't exist. Check application logs:
```bash
# View real-time logs
tail -f logs/app.log

# Search for errors
grep -i "ERROR" logs/app.log
```

## 🔄 Development Workflow

1. **Make changes** to code
2. **Test locally** with `uvicorn main:app --reload`
3. **Check logs** in `logs/app.log`
4. **Commit changes** to git
5. **Deploy** to Azure Container Apps

## 📝 Next Steps

- [ ] Enhance campaign analysis to support more objectives (e.g., Traffic, Conversion).
- [ ] Implement robust user authentication with OAuth2.
- [ ] Expand analytics capabilities with more detailed reporting endpoints.
- [ ] Develop a frontend interface for a more user-friendly experience.
- [ ] Integrate automated testing (unit and integration tests).
- [ ] Add comprehensive monitoring and alerting for production.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

---

**Need help?** Check the logs in `logs/app.log` or open an issue in the repository.
