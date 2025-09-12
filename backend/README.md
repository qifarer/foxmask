# Foxmask - 知识管理平台

Foxmask 是一个基于 FastAPI + GraphQL 的知识管理平台，支持多种数据源的知识采集、处理和检索。

## 功能特性

- 多源知识采集（文件、网页、API数据等）
- 知识条目管理与处理
- 向量化存储与检索（Weaviate）
- 知识图谱构建（Neo4j）
- 基于Casdoor的认证授权
- 分布式任务处理（Kafka）
- GraphQL API

## 技术栈

- **后端框架**: FastAPI + Strawberry (GraphQL)
- **数据库**: MongoDB (Beanie ODM)
- **文件存储**: MinIO
- **消息队列**: Kafka
- **向量数据库**: Weaviate
- **图数据库**: Neo4j
- **认证授权**: Casdoor

## 快速开始

1. 克隆项目并安装依赖
   ```bash
   pip install -r requirements.txt