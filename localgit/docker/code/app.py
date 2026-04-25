from flask import Flask, request, jsonify
import os
import subprocess
import shutil

app = Flask(__name__)
REPOS_DIR = "/git"

def is_valid_repo_name(name):
    if not name or len(name) > 100:
        return False
    # Basic safety: no path traversal, no special chars that break git
    forbidden = ['/', '\\', '..', ' ', '\t', '\n']
    return not any(char in name for char in forbidden) and name[0].isalnum()

@app.route("/api/repos", methods=["POST"])
def create_repo():
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if not is_valid_repo_name(name):
        return jsonify({"error": "Invalid repo name. Use only letters, numbers, -, _ (no spaces or special chars)"}), 400

    repo_path = os.path.join(REPOS_DIR, f"{name}.git")

    if os.path.exists(repo_path):
        return jsonify({"error": "Repository already exists"}), 409

    try:
        os.makedirs(repo_path, exist_ok=True)
        subprocess.check_call(["git", "init", "--bare", repo_path], cwd=REPOS_DIR)
        subprocess.check_call(["git", "-C", repo_path, "config", "http.receivepack", "true"])

        # Optional: nice description file
        with open(os.path.join(repo_path, "description"), "w") as f:
            f.write(f"Local Git repo created via API\n")

        return jsonify({
            "name": name,
            "clone_url": f"http://localhost/git/{name}.git",
            "message": "Repository created successfully. You can now git clone and push."
        }), 201
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Git command failed: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/repos", methods=["GET"])
def list_repos():
    repos = []
    try:
        for item in os.listdir(REPOS_DIR):
            if item.endswith(".git") and os.path.isdir(os.path.join(REPOS_DIR, item)):
                repos.append(item[:-4])
        return jsonify({"repos": sorted(repos)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Local Git Server with Flask API is running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
