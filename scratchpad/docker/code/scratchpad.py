# this is a simple scratchpad type web app for local networks. works well

from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Where we store the shared text (file-based, simplest possible)
DATA_FILE = "shared_scratchpad.txt"

# Make sure the file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write("")

@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>🏠 Local Scratchpad</title>
    <style>
        body {
            margin: 0;
            padding: 12px;
            font-family: -apple-system, BlinkMacOSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f11;
            color: #e0e0e0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
        }
        h1 {
            margin: 0 0 12px 0;
            font-size: 1.4rem;
            font-weight: 400;
            color: #888;
        }
        #editor {
            flex: 1;
            width: 100%;
            padding: 16px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 15px;
            line-height: 1.45;
            background: #111114;
            color: #e8e8f0;
            border: 1px solid #333;
            border-radius: 6px;
            resize: none;
            outline: none;
            box-sizing: border-box;
        }
        #controls {
            margin-top: 10px;
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }
        button {
            padding: 8px 16px;
            background: #2a2a3a;
            color: #ccc;
            border: 1px solid #444;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        button:hover {
            background: #36364f;
        }
        button:active {
            background: #404060;
        }
        #status {
            color: #777;
            font-size: 0.85rem;
        }
        .saved { color: #4caf50; }
        .saving { color: #ff9800; }
    </style>
</head>
<body>
    <h1>🏠 Local Network Scratchpad</h1>
    <textarea id="editor" spellcheck="false"></textarea>
    
    <div id="controls">
        <button onclick="save()">Save Now</button>
        <span id="status">Ready...</span>
    </div>

    <script>
        const editor = document.getElementById('editor');
        const status = document.getElementById('status');
        let lastSavedContent = '';
        let saveTimeout = null;
        const AUTO_SAVE_DELAY = 1500; // ms

        // Load initial content
        fetch('/get')
            .then(r => r.text())
            .then(text => {
                editor.value = text;
                lastSavedContent = text;
            })
            .catch(err => {
                status.textContent = 'Error loading content';
                status.className = '';
            });

        function showStatus(msg, className = '') {
            status.textContent = msg;
            status.className = className;
        }

        function save() {
            if (saveTimeout) clearTimeout(saveTimeout);
            
            const content = editor.value;
            if (content === lastSavedContent) return;

            showStatus('Saving...', 'saving');

            fetch('/save', {
                method: 'POST',
                headers: {'Content-Type': 'text/plain'},
                body: content
            })
            .then(r => {
                if (!r.ok) throw new Error('Save failed');
                lastSavedContent = content;
                showStatus('Saved ✓', 'saved');
                setTimeout(() => showStatus(''), 2000);
            })
            .catch(err => {
                showStatus('Save failed!', '');
                console.error(err);
            });
        }

        // Auto-save on typing (debounced)
        editor.addEventListener('input', () => {
            if (saveTimeout) clearTimeout(saveTimeout);
            showStatus('Will auto-save soon...');
            saveTimeout = setTimeout(save, AUTO_SAVE_DELAY);
        });

        // Optional: Ctrl/Cmd + S to save
        document.addEventListener('keydown', e => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                save();
            }
        });
    </script>
</body>
</html>
    """

@app.route('/get', methods=['GET'])
def get_content():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

@app.route('/save', methods=['POST'])
def save_content():
    try:
        content = request.get_data(as_text=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return "OK", 200
    except:
        return "Error", 500

if __name__ == '__main__':
    print("Starting local scratchpad...")
    print("Open on any device in your network: http://<your-computer-ip>:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)