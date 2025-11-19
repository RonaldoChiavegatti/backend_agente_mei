# Use the same base image as the API for consistency
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Set the PYTHONPATH
ENV PYTHONPATH="/app"

# Copy and install dependencies
COPY services/document_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Command to run the worker script as a module
CMD ["python", "-m", "services.document_service.infrastructure.worker.main"]
