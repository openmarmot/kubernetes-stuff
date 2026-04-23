#!/bin/bash
set -e

IMAGE_NAME="network-stats"
NAMESPACE="network-stats"
IMAGE_TAG=$(date +%Y%m%d%H%M%S)
export IMAGE_TAG NAMESPACE

echo "=== Building Docker image ==="
docker build -t ${IMAGE_NAME}:${TAG} -f docker/Dockerfile docker/

echo "=== Importing image into K3s containerd ==="
docker save ${IMAGE_NAME}:${TAG} | sudo k3s ctr images import -

echo "=== Creating namespace if not exists ==="
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

echo "=== Applying K3s deployment ==="
envsubst < k3s/deploy.yaml | kubectl apply -f - -n ${NAMESPACE}

echo "=== Waiting for rollout ==="
kubectl rollout status deployment/network-stats -n ${NAMESPACE}

echo "=== Network Stats deployed! ==="
echo "Access at: http://$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}'):$(kubectl get svc network-stats -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}')"

echo "=== Cleaning up old Docker images ==="
docker image prune -f