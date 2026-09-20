FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8501
# Default: conversational UI. For the API use:
#   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD streamlit run ui/streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}
