FROM python:3.11-slim
WORKDIR /app
COPY neuro_ghost/ ./neuro_ghost/
RUN pip install --no-cache-dir "mcp[cli]>=1.0.0,<2.0.0"
ENV MCP_TRANSPORT=sse
CMD ["python", "-m", "neuro_ghost.mcp_server"]
