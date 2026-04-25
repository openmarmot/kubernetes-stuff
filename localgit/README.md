# Local Git Server with Flask API (Docker)

A simple, no-authentication local Git server in one Docker container.

## Features
- Full Git clone/push/pull over HTTP (smart HTTP protocol via git-http-backend)
- REST API to create new repositories (`POST /api/repos`)
- List existing repos (`GET /api/repos`)
- Zero authentication (designed for local/trusted use only)
- Everything in a single lightweight container

## Quick Start

```bash
cd /path/to/this/folder
docker build -t local-git-server .
docker run -d --name git-server -p 8080:80 -v $(pwd)/repos:/git local-git-server
```

Then:

1. Create a new repo via API:
```bash
curl -X POST http://localhost:8080/api/repos \
  -H "Content-Type: application/json" \
  -d '{"name": "my-awesome-project"}'
```

2. Clone it:
```bash
git clone http://localhost:8080/git/my-awesome-project.git
```

3. Make changes and push (no credentials needed):
```bash
cd my-awesome-project
echo "Hello local git!" > README.md
git add .
git commit -m "Initial commit"
git push origin main
```

## API Endpoints

| Method | Endpoint       | Description                  | Example Body                  |
|--------|----------------|------------------------------|-------------------------------|
| POST   | /api/repos     | Create new bare repo         | `{"name": "my-project"}`      |
| GET    | /api/repos     | List all repos               | -                             |
| GET    | /api/health    | Health check                 | -                             |

## Notes
- Repos are stored in the mounted `/git` volume (persistent).
- Push is enabled automatically when creating via the API (`http.receivepack = true`).
- For security: Only run on localhost or trusted local network.
- Port 8080 on host → 80 inside container (change as needed).

## Why this setup?
- Uses battle-tested `git-http-backend` for correct Git protocol.
- Flask only handles the easy management API (repo creation).
- No need for SSH keys or passwords.

This is much simpler than a pure custom Git implementation while giving you the exact API you wanted.
