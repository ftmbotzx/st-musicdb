
from flask import Flask, render_template, render_template_string, request, jsonify, redirect, url_for
import os
import sys
import threading
import time
from datetime import datetime
import logging

# Add bot directory to path
sys.path.append('.')
from bot.database import DatabaseManager
from bot.handlers import indexing_process

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

# Initialize database
db = DatabaseManager()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        stats = db.get_statistics()
        return render_template_string(INDEX_TEMPLATE, stats=stats, indexing=indexing_process)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for getting database statistics"""
    try:
        stats = db.get_statistics()
        return jsonify({
            'success': True,
            'stats': stats,
            'indexing_status': {
                'active': indexing_process.get('active', False),
                'processed': indexing_process.get('processed', 0),
                'total': indexing_process.get('total', 0),
                'chat_id': indexing_process.get('chat_id'),
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search')
def api_search():
    """API endpoint for searching files"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': False, 'error': 'No search query provided'}), 400
    
    try:
        # Search by filename or track ID
        results = []
        
        # Try to find by filename
        file_by_name = db.find_file_by_name(query)
        if file_by_name:
            results.append(file_by_name)
        
        # Try to find by track ID
        file_by_track = db.find_file_by_track_id(query)
        if file_by_track and file_by_track not in results:
            results.append(file_by_track)
        
        return jsonify({
            'success': True,
            'results': results,
            'query': query
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/files')
def files_list():
    """Page showing all files in database"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = 50
        skip = (page - 1) * per_page
        
        files = db.get_all_files(limit=per_page, skip=skip)
        stats = db.get_statistics()
        total_pages = (stats['total_files'] + per_page - 1) // per_page
        
        return render_template_string(FILES_TEMPLATE, 
                                    files=files, 
                                    current_page=page,
                                    total_pages=total_pages,
                                    stats=stats)
    except Exception as e:
        logger.error(f"Error loading files: {e}")
        return f"Error loading files: {str(e)}", 500

@app.route('/export')
def export_page():
    """Export page"""
    return render_template_string(EXPORT_TEMPLATE)

@app.route('/api/export/<format>')
def api_export(format):
    """API endpoint for exporting database"""
    if format not in ['pdf', 'excel', 'csv']:
        return jsonify({'success': False, 'error': 'Invalid format'}), 400
    
    try:
        # This would trigger the export process
        # For now, just return a success message
        return jsonify({
            'success': True,
            'message': f'Export in {format} format initiated. Check your Telegram bot for the file.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# HTML Templates
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Media Indexer Bot - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2196F3; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2em; font-weight: bold; color: #2196F3; }
        .stat-label { color: #666; margin-top: 5px; }
        .indexing-status { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .status-active { color: #4CAF50; }
        .status-inactive { color: #666; }
        .nav-buttons { margin-bottom: 20px; }
        .btn { background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-right: 10px; display: inline-block; }
        .btn:hover { background: #1976D2; }
        .search-box { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .search-input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
        .search-results { margin-top: 20px; }
        .result-item { background: #f9f9f9; padding: 15px; border-radius: 4px; margin-bottom: 10px; border-left: 4px solid #2196F3; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Media Indexer Bot Dashboard</h1>
            <p>Monitor and manage your Telegram media indexing bot</p>
        </div>
        
        <div class="nav-buttons">
            <a href="/" class="btn">Dashboard</a>
            <a href="/files" class="btn">View Files</a>
            <a href="/export" class="btn">Export Data</a>
        </div>
        
        <div class="indexing-status">
            <h3>Indexing Status</h3>
            {% if indexing.get('active') %}
                <p class="status-active">✅ Active - Processing files...</p>
                <p>Chat ID: {{ indexing.get('chat_id', 'Unknown') }}</p>
                <p>Processed: {{ indexing.get('processed', 0) }} files</p>
            {% else %}
                <p class="status-inactive">⏸️ Inactive - Send a channel link to start indexing</p>
            {% endif %}
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_files }}</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.audio_files }}</div>
                <div class="stat-label">Audio Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.video_files }}</div>
                <div class="stat-label">Video Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.document_files }}</div>
                <div class="stat-label">Documents</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.photo_files }}</div>
                <div class="stat-label">Photos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.files_with_tracks }}</div>
                <div class="stat-label">With Track Info</div>
            </div>
        </div>
        
        <div class="search-box">
            <h3>Search Files</h3>
            <input type="text" id="searchInput" class="search-input" placeholder="Search by filename or track ID...">
            <div id="searchResults" class="search-results"></div>
        </div>
    </div>
    
    <script>
        let searchTimeout;
        document.getElementById('searchInput').addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchFiles(e.target.value);
            }, 500);
        });
        
        function searchFiles(query) {
            if (!query.trim()) {
                document.getElementById('searchResults').innerHTML = '';
                return;
            }
            
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    const resultsDiv = document.getElementById('searchResults');
                    if (data.success && data.results.length > 0) {
                        resultsDiv.innerHTML = data.results.map(file => `
                            <div class="result-item">
                                <strong>${file.file_name || 'Unknown'}</strong><br>
                                <small>Type: ${file.file_type} | Size: ${Math.round((file.file_size || 0) / 1024 / 1024 * 100) / 100} MB</small><br>
                                ${file.track_id ? `<small>Track ID: ${file.track_id}</small><br>` : ''}
                                ${file.track_url ? `<small>Track URL: ${file.track_url}</small><br>` : ''}
                                <small>Chat: ${file.chat_title} | Date: ${file.date}</small>
                            </div>
                        `).join('');
                    } else {
                        resultsDiv.innerHTML = '<p>No results found.</p>';
                    }
                })
                .catch(error => {
                    console.error('Search error:', error);
                    document.getElementById('searchResults').innerHTML = '<p>Search error occurred.</p>';
                });
        }
        
        // Auto-refresh stats every 30 seconds
        setInterval(() => {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload(); // Simple refresh for now
                    }
                })
                .catch(error => console.error('Stats refresh error:', error));
        }, 30000);
    </script>
</body>
</html>
"""

FILES_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Files - Media Indexer Bot</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2196F3; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .nav-buttons { margin-bottom: 20px; }
        .btn { background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-right: 10px; display: inline-block; }
        .btn:hover { background: #1976D2; }
        .files-table { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: bold; }
        .pagination { text-align: center; margin-top: 20px; }
        .page-btn { background: #2196F3; color: white; padding: 8px 12px; margin: 0 2px; text-decoration: none; border-radius: 4px; }
        .page-btn.current { background: #1976D2; }
        .file-type { padding: 3px 8px; border-radius: 12px; font-size: 12px; color: white; }
        .type-audio { background: #4CAF50; }
        .type-video { background: #FF9800; }
        .type-document { background: #2196F3; }
        .type-photo { background: #E91E63; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 Files Database</h1>
            <p>{{ stats.total_files }} total files indexed</p>
        </div>
        
        <div class="nav-buttons">
            <a href="/" class="btn">Dashboard</a>
            <a href="/files" class="btn">View Files</a>
            <a href="/export" class="btn">Export Data</a>
        </div>
        
        <div class="files-table">
            <table>
                <thead>
                    <tr>
                        <th>File Name</th>
                        <th>Type</th>
                        <th>Size</th>
                        <th>Track ID</th>
                        <th>Chat</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {% for file in files %}
                    <tr>
                        <td>{{ file.file_name or 'Unknown' }}</td>
                        <td><span class="file-type type-{{ file.file_type }}">{{ file.file_type.upper() }}</span></td>
                        <td>{{ (file.file_size / 1024 / 1024) | round(2) if file.file_size else 0 }} MB</td>
                        <td>{{ file.track_id or '-' }}</td>
                        <td>{{ file.chat_title or 'Unknown' }}</td>
                        <td>{{ file.date[:10] if file.date else '-' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        {% if total_pages > 1 %}
        <div class="pagination">
            {% for page_num in range(1, total_pages + 1) %}
                {% if page_num == current_page %}
                    <span class="page-btn current">{{ page_num }}</span>
                {% else %}
                    <a href="?page={{ page_num }}" class="page-btn">{{ page_num }}</a>
                {% endif %}
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

EXPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Export Data - Media Indexer Bot</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { background: #2196F3; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .nav-buttons { margin-bottom: 20px; }
        .btn { background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-right: 10px; display: inline-block; border: none; cursor: pointer; }
        .btn:hover { background: #1976D2; }
        .export-options { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .export-card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .export-card h3 { margin-top: 0; color: #2196F3; }
        .export-message { margin-top: 20px; padding: 15px; border-radius: 4px; display: none; }
        .export-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .export-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Export Database</h1>
            <p>Download your media database in different formats</p>
        </div>
        
        <div class="nav-buttons">
            <a href="/" class="btn">Dashboard</a>
            <a href="/files" class="btn">View Files</a>
            <a href="/export" class="btn">Export Data</a>
        </div>
        
        <div class="export-options">
            <div class="export-card">
                <h3>📄 PDF Export</h3>
                <p>Compact PDF with key metadata fields. Great for overview and sharing.</p>
                <button class="btn" onclick="exportData('pdf')">Export as PDF</button>
            </div>
            
            <div class="export-card">
                <h3>📊 Excel Export</h3>
                <p>Complete Excel file with ALL 30+ metadata fields. Perfect for detailed analysis.</p>
                <button class="btn" onclick="exportData('excel')">Export as Excel</button>
            </div>
            
            <div class="export-card">
                <h3>📋 CSV Export</h3>
                <p>Raw CSV data with all fields. Ideal for data processing and automation.</p>
                <button class="btn" onclick="exportData('csv')">Export as CSV</button>
            </div>
            
            <div id="exportMessage" class="export-message"></div>
        </div>
    </div>
    
    <script>
        function exportData(format) {
            const messageDiv = document.getElementById('exportMessage');
            messageDiv.style.display = 'block';
            messageDiv.className = 'export-message';
            messageDiv.innerHTML = `Initiating ${format.toUpperCase()} export...`;
            
            fetch(`/api/export/${format}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        messageDiv.className = 'export-message export-success';
                        messageDiv.innerHTML = `✅ ${data.message}`;
                    } else {
                        messageDiv.className = 'export-message export-error';
                        messageDiv.innerHTML = `❌ Export failed: ${data.error}`;
                    }
                })
                .catch(error => {
                    messageDiv.className = 'export-message export-error';
                    messageDiv.innerHTML = `❌ Export failed: ${error.message}`;
                });
        }
    </script>
</body>
</html>
"""

def run_flask_app():
    """Run Flask app in a separate thread"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_flask_app()
