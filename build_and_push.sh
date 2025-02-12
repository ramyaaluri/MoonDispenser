#!/bin/bash

# Variables
# TODO create an ECR repository and update the REPOSITORY_URI
REPOSITORY_URI="686255956204.dkr.ecr.us-east-1.amazonaws.com/moondispenser"
IMAGE_TAG="latest"

# Authenticate Docker to the Amazon ECR registry
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 686255956204.dkr.ecr.us-east-1.amazonaws.com

# Build the Docker image for linux/amd64 platform
docker buildx create --use
docker buildx build --platform linux/amd64 -t moondispenser --load .

# Tag the Docker image
docker tag moondispenser:latest $REPOSITORY_URI:$IMAGE_TAG

# Push the Docker image to ECR
docker push $REPOSITORY_URI:$IMAGE_TAG

echo "Docker image pushed to ECR: $REPOSITORY_URI:$IMAGE_TAG"