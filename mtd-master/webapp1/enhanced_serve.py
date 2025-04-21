import os
import uuid
import json
import redis
from flask import Flask, request, jsonify, Response, send_file, render_template_string
from werkzeug.utils import secure_filename
import requests as req
from markupsafe import escape

app = Flask("mtd_webapp")

# Redis configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-service")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

# Configure upload directory
UPLOAD_FOLDER = '/app/uploads'
DOWNLOAD_FOLDER = '/app/downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Predefined files for download testing
SAMPLE_FILES = {
    'small.txt': 1024 * 10,      # 10KB
    'medium.txt': 1024 * 1024,   # 1MB
    'large.txt': 10 * 1024 * 1024, # 10MB
    'huge.txt': 100 * 1024 * 1024  # 100MB
}

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Create sample files if they don't exist
def create_sample_files():
    for filename, size in SAMPLE_FILES.items():
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            app.logger.info(f"Creating sample file {filename} of size {size} bytes")
            with open(filepath, 'wb') as f:
                f.write(os.urandom(size))

# Function to get pod info for debugging
def get_pod_info():
    return {
        'pod_name': os.environ.get('HOSTNAME'),
        'pod_ip': os.environ.get('POD_IP'),
    }

@app.route("/", methods=["GET"])
def hello():
    session_id = request.cookies.get("session_id")
    pod_info = get_pod_info()
    generic_message = jsonify({
        "message": "Hello stranger",
        "pod_info": pod_info,
    }), 200

    if session_id is None:
        return generic_message

    app.logger.info(f"Request with session id {session_id[:10]}...")
    
    # Try to get session data from Redis
    user_data = redis_client.get(f"session:{session_id}")
    
    if user_data is None:
        return generic_message
    
    user = json.loads(user_data)["user"]
    app.logger.info(f"Request from user {user}")
    
    return jsonify({
        "message": f"Hello {user}",
        "pod_info": pod_info
    }), 200

@app.route("/login/<name>", methods=["PUT"])
def login(name):
    session_id = request.cookies.get("session_id")

    if session_id is None:
        session_id = uuid.uuid4().hex
        app.logger.info(f"Setting new session id {session_id[:10]}...")

    # Store session data in Redis
    redis_client.set(
        f"session:{session_id}", 
        json.dumps({"user": name}),
        ex=3600  # Set expiration to 1 hour
    )

    response = jsonify({
        "message": f"{name} is now logged in!",
        "pod_info": get_pod_info()
    })
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite='Strict')
    return response, 202

@app.route("/files", methods=["GET"])
def list_files():
    # List available files for download
    files = []
    
    # List predefined sample files
    for filename in SAMPLE_FILES.keys():
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            files.append({
                "name": filename,
                "size": size,
                "type": "sample"
            })
    
    # List uploaded files (if user is logged in)
    session_id = request.cookies.get("session_id")
    if session_id:
        user_data = redis_client.get(f"session:{session_id}")
        if user_data:
            user = json.loads(user_data)["user"]
            user_upload_dir = os.path.join(UPLOAD_FOLDER, user)
            if os.path.exists(user_upload_dir):
                for filename in os.listdir(user_upload_dir):
                    filepath = os.path.join(user_upload_dir, filename)
                    if os.path.isfile(filepath):
                        size = os.path.getsize(filepath)
                        files.append({
                            "name": filename,
                            "size": size,
                            "type": "user"
                        })
    
    return jsonify({
        "files": files,
        "pod_info": get_pod_info()
    }), 200

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    # First check if it's a sample file
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    
    # If not a sample file, check if it's a user-uploaded file
    if not os.path.exists(filepath):
        session_id = request.cookies.get("session_id")
        if session_id:
            user_data = redis_client.get(f"session:{session_id}")
            if user_data:
                user = json.loads(user_data)["user"]
                filepath = os.path.join(UPLOAD_FOLDER, user, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({
            "error": "File not found",
            "pod_info": get_pod_info()
        }), 404

@app.route("/upload", methods=["POST"])
def upload_file():
    session_id = request.cookies.get("session_id")
    if not session_id:
        return jsonify({
            "error": "Authentication required",
            "pod_info": get_pod_info()
        }), 401
    
    user_data = redis_client.get(f"session:{session_id}")
    if not user_data:
        return jsonify({
            "error": "Session expired",
            "pod_info": get_pod_info()
        }), 401
    
    user = json.loads(user_data)["user"]
    
    if 'file' not in request.files:
        return jsonify({
            "error": "No file part",
            "pod_info": get_pod_info()
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "error": "No selected file",
            "pod_info": get_pod_info()
        }), 400
    
    # Create user upload directory if it doesn't exist
    user_upload_dir = os.path.join(UPLOAD_FOLDER, user)
    os.makedirs(user_upload_dir, exist_ok=True)
    
    # Save the file
    filename = secure_filename(file.filename)
    filepath = os.path.join(user_upload_dir, filename)
    file.save(filepath)
    
    return jsonify({
        "message": "File uploaded successfully",
        "filename": filename,
        "size": os.path.getsize(filepath),
        "pod_info": get_pod_info()
    }), 201

@app.route("/health", methods=["GET"])
def health_check():
    # Simple health check endpoint
    return jsonify({
        "status": "ok",
        "pod_info": get_pod_info()
    }), 200

@app.route("/ui", methods=["GET"])
def ui():
    # A simple HTML UI for testing file uploads and downloads
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MTD Web Application</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { border: 1px solid #ddd; border-radius: 4px; padding: 20px; margin-bottom: 20px; }
            .btn { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
            .btn:hover { background-color: #45a049; }
            .file-list { margin-top: 20px; }
            .file-item { padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }
            #pod-info { font-size: 12px; color: #666; margin-top: 30px; }
            .reconnect-info { background-color: #f8f9fa; padding: 10px; border-left: 4px solid #17a2b8; margin-bottom: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>MTD Web Application</h1>
            
            <div class="reconnect-info">
                <p><strong>Connection Info:</strong> This app uses automatic reconnection if the connection is lost due to pod rotation or IP changes.</p>
            </div>
            
            <div class="card">
                <h2>Login</h2>
                <input type="text" id="username" placeholder="Enter username">
                <button class="btn" onclick="login()">Login</button>
                <div id="login-status"></div>
            </div>
            
            <div class="card">
                <h2>Upload File</h2>
                <input type="file" id="file-upload">
                <button class="btn" onclick="uploadFile()">Upload</button>
                <div id="upload-status"></div>
            </div>
            
            <div class="card">
                <h2>Available Files</h2>
                <button class="btn" onclick="listFiles()">Refresh File List</button>
                <div id="file-list" class="file-list"></div>
            </div>
            
            <div id="pod-info"></div>
        </div>
        
        <script>
            // Add reconnection logic and exponential backoff
            class ReconnectingFetch {
                constructor(maxRetries = 5, initialBackoff = 300) {
                    this.maxRetries = maxRetries;
                    this.initialBackoff = initialBackoff;
                }
                
                async fetch(url, options = {}) {
                    let retries = 0;
                    let backoff = this.initialBackoff;
                    
                    while (retries <= this.maxRetries) {
                        try {
                            const response = await fetch(url, options);
                            if (response.ok) {
                                return response;
                            }
                        } catch (error) {
                            console.log(`Request failed (attempt ${retries + 1}/${this.maxRetries + 1}): ${error.message}`);
                        }
                        
                        if (retries === this.maxRetries) {
                            break;
                        }
                        
                        // Wait before retrying with exponential backoff
                        await new Promise(resolve => setTimeout(resolve, backoff));
                        backoff *= 2; // Exponential backoff
                        retries++;
                    }
                    
                    throw new Error(`Failed after ${this.maxRetries + 1} attempts`);
                }
            }
            
            const rfetch = new ReconnectingFetch();
            
            async function login() {
                const username = document.getElementById('username').value;
                if (!username) {
                    alert('Please enter a username');
                    return;
                }
                
                try {
                    const response = await rfetch.fetch(`/login/${username}`, {
                        method: 'PUT',
                        credentials: 'same-origin'
                    });
                    const data = await response.json();
                    document.getElementById('login-status').innerText = data.message;
                    document.getElementById('pod-info').innerText = `Pod: ${data.pod_info.pod_name} (${data.pod_info.pod_ip})`;
                    listFiles();
                } catch (error) {
                    document.getElementById('login-status').innerText = `Error: ${error.message}`;
                }
            }
            
            async function uploadFile() {
                const fileInput = document.getElementById('file-upload');
                if (!fileInput.files.length) {
                    alert('Please select a file');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {
                    const response = await rfetch.fetch('/upload', {
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    });
                    const data = await response.json();
                    document.getElementById('upload-status').innerText = data.message;
                    document.getElementById('pod-info').innerText = `Pod: ${data.pod_info.pod_name} (${data.pod_info.pod_ip})`;
                    listFiles();
                } catch (error) {
                    document.getElementById('upload-status').innerText = `Error: ${error.message}`;
                }
            }
            
            async function listFiles() {
                try {
                    const response = await rfetch.fetch('/files', {
                        credentials: 'same-origin'
                    });
                    const data = await response.json();
                    const fileList = document.getElementById('file-list');
                    fileList.innerHTML = '';
                    
                    if (data.files.length === 0) {
                        fileList.innerHTML = '<p>No files available</p>';
                    } else {
                        data.files.forEach(file => {
                            const fileItem = document.createElement('div');
                            fileItem.className = 'file-item';
                            
                            const fileInfo = document.createElement('div');
                            fileInfo.innerText = `${file.name} (${formatSize(file.size)})`;
                            
                            const downloadBtn = document.createElement('button');
                            downloadBtn.className = 'btn';
                            downloadBtn.innerText = 'Download';
                            downloadBtn.onclick = () => { window.location.href = `/download/${file.name}`; };
                            
                            fileItem.appendChild(fileInfo);
                            fileItem.appendChild(downloadBtn);
                            fileList.appendChild(fileItem);
                        });
                    }
                    
                    document.getElementById('pod-info').innerText = `Pod: ${data.pod_info.pod_name} (${data.pod_info.pod_ip})`;
                } catch (error) {
                    document.getElementById('file-list').innerHTML = `<p>Error loading files: ${error.message}</p>`;
                }
            }
            
            function formatSize(bytes) {
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
                return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
            }
            
            // Initialize
            window.onload = function() {
                // Attempt to load files on page load
                listFiles();
                
                // Set up periodic health checks and pod info updates
                setInterval(async () => {
                    try {
                        const response = await rfetch.fetch('/health', {
                            credentials: 'same-origin'
                        });
                        const data = await response.json();
                        document.getElementById('pod-info').innerText = `Pod: ${data.pod_info.pod_name} (${data.pod_info.pod_ip})`;
                    } catch (error) {
                        console.error('Health check failed:', error);
                    }
                }, 5000);
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == "__main__":
    create_sample_files()
    app.run(host="0.0.0.0", port=8080, debug=True)
