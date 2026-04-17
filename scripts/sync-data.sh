#!/bin/bash

echo "Syncing local data to cloud storage..."

# AWS S3
if command -v aws &> /dev/null; then
    echo "Syncing to AWS S3..."
    aws s3 sync data/ s3://your-vcp-bucket/data/ --delete
    aws s3 sync outputs/ s3://your-vcp-bucket/outputs/ --delete
fi

# Azure Blob
if command -v az &> /dev/null; then
    echo "Syncing to Azure Blob..."
    az storage blob upload-batch --source data --destination '$web/data' --account-name yourstorage
fi

# Google Cloud Storage
if command -v gsutil &> /dev/null; then
    echo "Syncing to GCS..."
    gsutil -m rsync -r data/ gs://your-vcp-bucket/data/
    gsutil -m rsync -r outputs/ gs://your-vcp-bucket/outputs/
fi

echo "Data sync complete!"
