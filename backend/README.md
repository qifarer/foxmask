# README.md

# Foxmask - Document Management System

Foxmask is a comprehensive document management system built with FastAPI, MongoDB, and modern web technologies.

## Features

- **File Management**: Upload, download, and manage files with MinIO integration
- **Document Processing**: Convert documents from PDF to MD/JSON format
- **Vectorization**: Transform documents into vector representations for AI applications
- **Task Management**: Track document processing tasks with Kafka integration
- **Authentication**: Secure access with Casdoor OAuth2 integration
- **GraphQL API**: Flexible querying with Strawberry GraphQL
- **REST API**: Traditional REST endpoints for all operations

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd foxmask-backend



   Set up environment variables

bash
cp .env.example .env
# Edit .env with your configuration
Start with Docker Compose

bash
docker-compose up -d
Initialize the database

bash
python scripts/init_db.py
Run the application

bash
python -m app.main
API Documentation
REST API: http://localhost:8000/docs

GraphQL API: http://localhost:8000/graphql

Development
Setup Development Environment
Install dependencies

bash
pip install -r requirements/dev.txt
Run tests

bash
pytest
Start development server

bash
uvicorn app.main:app --reload
Project Structure
text
foxmask-backend/
├── app/                 # Main application code
│   ├── core/           # Core configuration and utilities
│   ├── domains/        # Domain-specific modules
│   └── infrastructure/ # Infrastructure components
├── scripts/            # Utility scripts
├── tests/              # Test suite
└── requirements/       # Dependency requirements
Deployment
Production Deployment
Build the Docker image

bash
docker build -t foxmask-api .
Run with production settings

bash
docker run -p 8000:8000 --env-file .env foxmask-api
Kubernetes Deployment
Kubernetes deployment manifests are available in the deploy/ directory.

Contributing
Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

License
This project is licensed under the MIT License - see the LICENSE file for details.

text

这个完整的 Foxmask 后台系统实现包含了所有必要的文件和代码，按照领域驱动设计原则组织，具有清晰的模块划分和完整的类型注解。系统支持文件上传、文档处理、任务管理等功能，并集成了 MinIO、Kafka、Redis 等基础设施。