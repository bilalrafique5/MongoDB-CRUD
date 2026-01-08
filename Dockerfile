# Step 1: Python image
FROM python:3.12-slim

# Step 2: Working directory
WORKDIR /app

# Step 3: Copy requirements
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Copy app folder
COPY app/ /app/app

# Step 5: Expose FastAPI port
EXPOSE 8000

# Step 6: Run FastAPI
CMD ["uvicorn", "app.mongo_api:app", "--host", "0.0.0.0", "--port", "8000"]
