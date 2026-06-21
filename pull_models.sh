#!/bin/bash
echo "Waiting for Ollama to finish installing..."
while ! command -v ollama &> /dev/null; do
    sleep 30
done

echo "Ollama is installed. Waiting for daemon to start..."
while ! curl -s http://localhost:11434/api/tags &> /dev/null; do
    sleep 10
done

echo "Pulling models..."
ollama pull qwen2:0.5b
ollama pull hf.co/unsloth/Llama-3.2-3B-Instruct-GGUF:latest
ollama pull llama3.2
ollama pull llama3.1

echo "All models downloaded successfully!"
