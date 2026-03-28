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

# Build with the localhost prefix that Podman forces
docker build -t "localhost/${container_name}:${container_tag}" .

# Import into containerd
docker save "localhost/${container_name}:${container_tag}" | \
  k3s ctr -n k8s.io images import -

# Create short-name alias so your deploy.yaml works without any change
sudo k3s ctr -n k8s.io images tag \
  "localhost/${container_name}:${container_tag}" \
  "${container_name}:${container_tag}"

echo "Image imported as both localhost/... and ${container_name}:..."

# ====================== DEPLOY ======================
echo "=== Deploying to Kubernetes ==="
cd ../k3s || { echo "k3s/ directory not found"; exit 1; }

# Create namespace idempotently
kubectl create namespace "${namespace_name}" --dry-run=client -o yaml | \
  kubectl apply -f -

# Render + apply (same as before)
env \
  namespace_name="${namespace_name}" \
  container_name="${container_name}" \
  kubernetes_name="${kubernetes_name}" \
  container_port="${container_port}" \
  container_tag="${container_tag}" \
  envsubst < ./deploy.yaml | kubectl apply -f -

# Wait for the pod to actually start using the image before pruning
echo "=== Waiting for deployment rollout ==="
kubectl rollout status deployment/"${kubernetes_name}-deployment" \
  --namespace "${namespace_name}" --timeout=60s

# ====================== STATUS ======================
echo "=== Current resources ==="
kubectl get all --namespace "${namespace_name}"

echo -e "\n=== NodePort (external access) ==="
kubectl get service "${kubernetes_name}-service" \
  --namespace "${namespace_name}" \
  -o jsonpath='{.spec.ports[0].nodePort}'

# ====================== FINAL CLEANUP ======================
echo "=== Pruning old unused images (new one is now in use) ==="
k3s crictl rmi --prune