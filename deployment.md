# 1. Install all dependencies
pip install -r requirements.txt

# 2. Install and setup Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:8b

# 3. Create necessary directories
mkdir -p logs database/vector_db

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Test individual MCP servers
python mcp_servers/database/database_mcp_server.py &
python mcp_servers/logging/logging_mcp_server.py &
python mcp_servers/calendar/calendar_mcp_server.py &

# 6. Test CEO Agent system
python test_ceo_agent_client.py

# 7. Run web interface
streamlit run main.py

# 8. Test with MCP Inspector
npx @modelcontextprotocol/inspector python mcp_servers/database/database_mcp_server.py