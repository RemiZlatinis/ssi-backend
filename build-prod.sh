#!/bin/bash
# Build script for production Podman image

# Get version from pyproject.toml
VERSION=$(grep -E '^version = ' pyproject.toml | sed -E 's/version = "(.*)"/\1/')

# If no version found, use git commit hash
if [ -z "$VERSION" ]; then
    VERSION=$(git rev-parse --short HEAD)
fi

# Build the production image with version tag
echo "Building ssi-backend:prod-$VERSION"
podman build -f Dockerfile.prod -t ssi-backend:prod-$VERSION .

# Also tag as latest
podman tag ssi-backend:prod-$VERSION ssi-backend:prod

echo "Production image built successfully!"
echo "Tags: ssi-backend:prod-$VERSION and ssi-backend:prod"
echo "To run the containers, use: podman-compose -f docker-compose.prod.yml up"
