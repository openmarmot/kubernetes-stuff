#!/bin/bash

# substitute variables and deploy to kubernetes


#set -e

# -- variables --
namespace_name="keycloak"
container_name="keycloak"
kubernetes_name="keycloak"
image_and_tag="quay.io/keycloak/keycloak:26.3.3"

kubectl create namespace ${namespace_name}

# this is so env variables in the yaml get evaluated
eval "cat <<EOF
$(<./app.yaml)
EOF
" | kubectl apply -f -

echo  "kubectl get all --namespace ${namespace_name}"
kubectl get all --namespace ${namespace_name}
