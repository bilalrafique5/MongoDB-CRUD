# Step 1: Use official Python image
FROM python:3.12-slim

# Step 2: Set working directory
WORKDIR /app

# Step 3: Copy requirements
COPY app/requirements.txt .

# Step 4: Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of the app
COPY app/ /app

# Step 6: Expose port 8000
EXPOSE 8000

# Step 7: Run FastAPI
CMD ["uvicorn", "mongo_api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
