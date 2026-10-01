FROM python:3.12-slim

# Install C++ compiler
RUN apt-get update && apt-get install -y g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire project
COPY . /app

# Install Python dependencies if a requirements file exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Default command runs the generator (override as needed)
ENTRYPOINT ["python", "generate_tests.py"]
