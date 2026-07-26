# kubernetes-stuff
holding repo for misc kubernetes deployments and other stuff

Designed to be cloned down to a single node k3s server. 
Run build_and_deploy_k3s.sh as root to update/deploy an app.  

## Folders

- `scratchpad/` - simple scratchpad website to share text on a local network
- `mdictate/`   - browser speech-to-text UI (Flask); whisper.cpp stays a manual host process
- `mfileserve/` - simple http file server to share/serve files on a local network
- `mattermost/` - like slack. works well with hermes agent
- `keycloak/`   - its keycloak
- `opencode/`   - opencode web server that also configures itself
