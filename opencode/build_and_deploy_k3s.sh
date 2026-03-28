#!/bin/bash

# build → import → deploy on k3s
# run as root on the k3s server

set -e

# ====================== VARIABLES ======================
namespace_name="opencode"
container_name="opencode"
kubernetes_name="opencode"
container_port=5000
container_tag=$(date +%b-%d-%Y-%k-%M)

# ====================== BUILD & IMPORT ======================
echo "=== Building and importing image ==="
cd docker || { echo "docker/ directory not found"; exit 1; }

docker build -t "${container_name}:${container_tag}" .

docker save "${container_name}:${container_tag}" | \
  k3s ctr -n k8s.io images import -

# ====================== DEPLOY ======================
echo "=== Deploying to Kubernetes ==="
cd ../k3s || { echo "k3s/ directory not found"; exit 1; }

# Create namespace idempotently (safe to run every time)
kubectl create namespace "${namespace_name}" --dry-run=client -o yaml | \
  kubectl apply -f -

# Substitute variables and apply
# (much cleaner & safer than eval)
envsubst < ./deploy.yaml | kubectl apply -f -

# ====================== STATUS ======================
echo "=== Current resources ==="
kubectl get all --namespace "${namespace_name}"

echo -e "\n=== NodePort for external access ==="
kubectl get service "${kubernetes_name}-service" \
  --namespace "${namespace_name}" \
  -o jsonpath='{.spec.ports[0].nodePort}'

# ====================== CLEANUP ======================
echo "=== Pruning unused images ==="
k3s crictl rmi --prune