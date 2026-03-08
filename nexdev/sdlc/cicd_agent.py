#!/usr/bin/env python3
"""
NexDev Phase 3.1 — CI/CD Pipeline Ownership
=============================================
DevOps agent that manages builds, tests, deployments, and rollbacks.
Generates GitHub Actions, Docker configs, and deployment manifests.
"""

import json
from typing import Dict, List
from datetime import datetime


class CICDAgent:
    """DevOps agent for CI/CD pipeline management."""
    
    def generate_github_actions(self, project_config: Dict) -> Dict:
        """Generate GitHub Actions workflow files."""
        tech = project_config.get("tech_stack", {})
        has_docker = "docker" in str(tech).lower()
        is_python = "python" in tech.get("backend", "").lower()
        is_node = "node" in tech.get("backend", "").lower()
        
        # CI workflow
        ci_workflow = self._gen_ci_workflow(is_python, is_node, has_docker)
        
        # CD workflow
        cd_workflow = self._gen_cd_workflow(project_config)
        
        # PR checks
        pr_workflow = self._gen_pr_workflow(is_python, is_node)
        
        return {
            "files": [
                {"path": ".github/workflows/ci.yml", "content": ci_workflow, "description": "Continuous Integration"},
                {"path": ".github/workflows/cd.yml", "content": cd_workflow, "description": "Continuous Deployment"},
                {"path": ".github/workflows/pr-checks.yml", "content": pr_workflow, "description": "PR Quality Checks"},
            ]
        }
    
    def _gen_ci_workflow(self, is_python: bool, is_node: bool, has_docker: bool) -> str:
        test_step = ""
        if is_python:
            test_step = """
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest --cov=app --cov-report=xml -v
      - uses: codecov/codecov-action@v4"""
        elif is_node:
            test_step = """
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test -- --coverage
      - run: npm run lint"""
        
        docker_step = ""
        if has_docker:
            docker_step = """
  docker:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: app:test
          cache-from: type=gha
          cache-to: type=gha,mode=max"""
        
        return f"""name: CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4{test_step}
{docker_step}"""
    
    def _gen_cd_workflow(self, config: Dict) -> str:
        return """name: CD
on:
  push:
    branches: [main]
    
concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ secrets.ECR_REGISTRY }}/app:${{ github.sha }}
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \\
            --cluster production \\
            --service app \\
            --force-new-deployment
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1
      
      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \\
            --cluster production \\
            --services app
      
      - name: Smoke test
        run: |
          for i in {1..5}; do
            status=$(curl -s -o /dev/null -w '%{http_code}' ${{ secrets.APP_URL }}/api/health)
            if [ "$status" = "200" ]; then exit 0; fi
            sleep 10
          done
          echo "Smoke test failed" && exit 1
      
      - name: Rollback on failure
        if: failure()
        run: |
          aws ecs update-service \\
            --cluster production \\
            --service app \\
            --task-definition $(aws ecs describe-services --cluster production --services app --query 'services[0].taskDefinition' --output text)
"""
    
    def _gen_pr_workflow(self, is_python: bool, is_node: bool) -> str:
        lint_step = ""
        if is_python:
            lint_step = """
      - run: pip install ruff mypy
      - run: ruff check .
      - run: mypy app/ --ignore-missing-imports"""
        elif is_node:
            lint_step = """
      - run: npm ci
      - run: npm run lint
      - run: npx tsc --noEmit"""
        
        return f"""name: PR Checks
on:
  pull_request:
    branches: [main, develop]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4{lint_step}
  
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: {'python' if is_python else 'javascript'}
      - uses: github/codeql-action/analyze@v3
"""
    
    def generate_docker_compose(self, config: Dict) -> str:
        """Generate docker-compose for local development."""
        return """version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
      - SECRET_KEY=dev-secret-key
      - DEBUG=true
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
"""
    
    def generate_terraform(self, config: Dict) -> List[Dict]:
        """Generate basic Terraform for AWS infrastructure."""
        return [
            {
                "path": "infra/main.tf",
                "content": """terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket = "terraform-state"
    key    = "app/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" { region = var.region }

variable "region" { default = "us-east-1" }
variable "environment" { default = "production" }

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  name    = "${var.environment}-vpc"
  cidr    = "10.0.0.0/16"
  azs             = ["${var.region}a", "${var.region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  enable_nat_gateway = true
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-cluster"
  setting { name = "containerInsights" value = "enabled" }
}

# RDS PostgreSQL
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"
  identifier     = "${var.environment}-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.medium"
  allocated_storage = 20
  db_name  = "app"
  username = "app_admin"
  vpc_security_group_ids = [aws_security_group.db.id]
  subnet_ids = module.vpc.private_subnets
  multi_az = var.environment == "production"
}

# Security Groups
resource "aws_security_group" "db" {
  name_prefix = "${var.environment}-db-"
  vpc_id      = module.vpc.vpc_id
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}
""",
            },
        ]


if __name__ == "__main__":
    cicd = CICDAgent()
    
    config = {"tech_stack": {"backend": "Python (FastAPI)", "database": "PostgreSQL"}}
    result = cicd.generate_github_actions(config)
    print(f"Generated {len(result['files'])} CI/CD files:")
    for f in result["files"]:
        print(f"  {f['path']} — {f['description']}")
    
    compose = cicd.generate_docker_compose(config)
    print(f"\nDocker Compose: {compose.count(chr(10))} lines")
    
    tf = cicd.generate_terraform(config)
    print(f"Terraform: {len(tf)} files")
    print("\n✅ CI/CD Agent tested")
