#!/bin/bash

# build → import → deploy on k3s (Podman + containerd fixed)
# run as root on the k3s server
#
# mdictate = speech-to-text web UI (Flask). whisper.cpp stays a manual host process.

set -e

# ====================== VARIABLES ======================
namespace_name="mdictate"
container_name="mdictate"
kubernetes_name="mdictate"
container_port=5000
container_tag=$(date +%b-%d-%Y-%H-%M)

# Default whisper.cpp URL pre-filled in the UI.
# Pod network cannot reach host "localhost" — default to this machine's first
# non-loopback IPv4 so same-node whisper.cpp on :8025 works out of the box.
# Override when deploying, e.g.:
#   default_whisper_url=http://10.12.0.51:8025 ./build_and_deploy_k3s.sh
if [ -z "${default_whisper_url:-}" ]; then
  _host_ip=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' | grep -v '^127\.' | head -n1 || true)
  if [ -n "${_host_ip}" ]; then
    default_whisper_url="http://${_host_ip}:8025"
  else
    default_whisper_url="http://127.0.0.1:8025"
  fi
fi
echo "=== Default whisper URL for UI: ${default_whisper_url}"

# ====================== CLEANUP OLD IMAGES FIRST ======================
echo "=== Pruning old unused images from k3s ==="
k3s crictl rmi --prune

# ====================== BUILD & IMPORT ======================
echo "=== Building and importing image ==="
cd docker || { echo "docker/ directory not found"; exit 1; }

# Build with the localhost/ prefix that Podman forces
docker build -t "localhost/${container_name}:${container_tag}" .

# Import into containerd
docker save "localhost/${container_name}:${container_tag}" | \
  k3s ctr -n k8s.io images import -

echo "✅ Image imported as localhost/${container_name}:${container_tag}"

# ====================== DEPLOY ======================
echo "=== Deploying to Kubernetes ==="
cd ../k3s || { echo "k3s/ directory not found"; exit 1; }

# Create namespace idempotently
kubectl create namespace "${namespace_name}" --dry-run=client -o yaml | \
  kubectl apply -f -

# Render + apply (with variables substituted)
env \
  namespace_name="${namespace_name}" \
  container_name="${container_name}" \
  kubernetes_name="${kubernetes_name}" \
  container_port="${container_port}" \
  container_tag="${container_tag}" \
  default_whisper_url="${default_whisper_url}" \
  envsubst < ./deploy.yaml | kubectl apply -f -

# Wait for the pod to actually start using the image
echo "=== Waiting for deployment rollout ==="
kubectl rollout status deployment/"${kubernetes_name}-deployment" \
  --namespace "${namespace_name}" --timeout=90s

# ====================== STATUS ======================
echo "=== Current resources ==="
kubectl get all --namespace "${namespace_name}"

echo -e "\n=== NodePort (external access) ==="
node_port=$(kubectl get service "${kubernetes_name}-service" \
  --namespace "${namespace_name}" \
  -o jsonpath='{.spec.ports[0].nodePort}')
echo "https (NodePort): ${node_port}"
echo "Open: https://<node-ip>:${node_port}/  (accept self-signed cert for mic access)"
echo "whisper.cpp is manual — UI default: ${default_whisper_url}"
echo "Override default at deploy time: default_whisper_url=http://<host>:8025 $0"

# ====================== HOST CLEANUP (Docker/Podman) ======================
echo "=== Cleaning up old Docker/Podman images and build cache ==="
# Removes dangling images + old timestamped images that are no longer used
docker image prune -f

# Cleans build cache older than 48 hours (keeps recent builds fast)
docker builder prune -f --filter "until=48h"

echo "✅ Host cleanup complete"
