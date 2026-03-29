#!/bin/bash

# Mattermost + Postgres deploy on k3s (adapted from your template)
# Run as root on the k3s server

set -e

# ====================== VARIABLES ======================
namespace_name="mattermost"
mattermost_image_tag="release-11"
mattermost_node_port=30065

# Auto-detect k3s node IP (works on single-node k3s)
node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' | head -n1)

if [ -z "$node_ip" ]; then
  echo "❌ Could not auto-detect node IP. Please set 'node_ip=your.ip.here' manually in the script."
  exit 1
fi

echo "=== Deploying Mattermost to namespace: $namespace_name ==="
echo "Node IP detected : $node_ip"
echo "Mattermost will be available at: http://$node_ip:$mattermost_node_port"

# ====================== PASSWORD PROMPT ======================

echo -e "\nPlease enter a strong password for the PostgreSQL database (mmuser):"
while true; do
  read -s -p "Password: " db_password
  echo
  read -s -p "Confirm password: " db_password_confirm
  echo

  if [ "$db_password" = "$db_password_confirm" ] && [ -n "$db_password" ]; then
    break
  else
    echo "❌ Passwords do not match or are empty. Please try again."
  fi
done

echo "✅ Password accepted."

# ====================== DEPLOY ======================
echo "=== Deploying to Kubernetes ==="
cd k3s || { echo "k3s/ directory not found"; exit 1; }

# Create namespace idempotently
kubectl create namespace "${namespace_name}" --dry-run=client -o yaml | \
  kubectl apply -f -

# Render + apply Postgres
echo "→ Applying Postgres..."
env \
  namespace_name="${namespace_name}" \
  db_password="${db_password}" \
  envsubst < ./postgres.yaml | kubectl apply -f -

# Render + apply Mattermost
echo "→ Applying Mattermost..."
env \
  namespace_name="${namespace_name}" \
  db_password="${db_password}" \
  node_ip="${node_ip}" \
  mattermost_image_tag="${mattermost_image_tag}" \
  mattermost_node_port="${mattermost_node_port}" \
  envsubst < ./mattermost.yaml | kubectl apply -f -

# Wait for rollout
echo "=== Waiting for deployments to roll out ==="
kubectl rollout status deployment/postgres-deployment --namespace "${namespace_name}" --timeout=120s
kubectl rollout status deployment/mattermost-deployment --namespace "${namespace_name}" --timeout=180s

# ====================== STATUS ======================
echo "=== Current resources ==="
kubectl get all --namespace "${namespace_name}"

echo -e "\n=== Mattermost Access ==="
echo "Web UI → http://${node_ip}:${mattermost_node_port}"
echo "First startup takes ~1-2 minutes (DB schema creation). Then create your admin account."