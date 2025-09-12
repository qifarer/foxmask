#!/bin/bash

# Set environment variables for testing
export MONGODB_URI=mongodb://localhost:27017
export MONGODB_DB_NAME=foxmask_test
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export MINIO_BUCKET_NAME=foxmask-test
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_KNOWLEDGE_TOPIC=knowledge_processing_test
export CASDOOR_ENDPOINT=https://casdoor.example.com
export CASDOOR_CLIENT_ID=test_client_id
export CASDOOR_CLIENT_SECRET=test_client_secret
export CASDOOR_CERT=test_cert
export CASDOOR_ORG_NAME=test_org
export WEAVIATE_URL=http://localhost:8080
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=test_password
export APP_SECRET_KEY=test_secret_key
export DEBUG=True

# Run tests
echo "Running unit tests..."
pytest tests/unit/ -v --cov=.

echo "Running integration tests..."
pytest tests/integration/ -v --cov=. --cov-append

echo "Running end-to-end tests..."
pytest tests/e2e/ -v --cov=. --cov-append

echo "Generating coverage report..."
coverage html