## Run the chat frontend

From the project root, start the API and frontend with the project virtual environment:

```bash
./src/.venv/Scripts/python.exe -m src.main
```

Then open http://localhost:8000 in a browser. The page sends messages to the `/chat` endpoint and creates a conversation ID automatically.

Do not run `python -m main`; the application entry point is `src.main`.

## Free local model

The agent uses Ollama locally, so it does not use Gemini API quota. Install Ollama, then run:

```bash
ollama pull qwen2.5:7b
```

Ollama should be running before starting the API. You can change the model with `OLLAMA_MODEL` in `.env`.
