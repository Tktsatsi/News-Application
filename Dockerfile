FROM python:3.13.5-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
# Set the working directory in the container
ENV PYTHONPATH=/app

WORKDIR /app

# Install system deps needed for mysqlclient and others
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/
# Install dependencies and update pip to the latest version
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port 8000 for the Django app
EXPOSE 8000

# Start the Django development server
CMD ["python", "News_app/manage.py", "runserver", "0.0.0.0:8000"]
