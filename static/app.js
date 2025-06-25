// Global application state
const app = {
    connected: false,
    downloading: false,
    connectionStatus: 'disconnected'
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Check initial connection status
    checkConnectionStatus();
    
    // Set up connection form
    const connectionForm = document.getElementById('connection-form');
    if (connectionForm) {
        connectionForm.addEventListener('submit', handleConnection);
    }
    
    // Set up periodic status updates
    setInterval(checkConnectionStatus, 5000);
}

async function checkConnectionStatus() {
    try {
        const response = await fetch('/api/connection/status');
        const status = await response.json();
        
        updateConnectionStatus(status.connected);
        app.connected = status.connected;
        
    } catch (error) {
        console.error('Failed to check connection status:', error);
        updateConnectionStatus(false);
    }
}

function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    const connectBtn = document.getElementById('connect-btn');
    
    if (!statusElement) return;
    
    if (connected) {
        statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Connected';
        statusElement.className = 'badge status-connected';
        
        if (connectBtn) {
            connectBtn.innerHTML = '<i class="fas fa-unlink me-2"></i>Disconnect';
            connectBtn.className = 'btn btn-danger w-100';
        }
    } else {
        statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Disconnected';
        statusElement.className = 'badge status-disconnected';
        
        if (connectBtn) {
            connectBtn.innerHTML = '<i class="fas fa-plug me-2"></i>Connect';
            connectBtn.className = 'btn btn-primary w-100';
        }
    }
    
    app.connectionStatus = connected ? 'connected' : 'disconnected';
}

async function handleConnection(event) {
    event.preventDefault();
    
    const connectBtn = document.getElementById('connect-btn');
    const statusElement = document.getElementById('connection-status');
    
    if (app.connected) {
        // Disconnect
        try {
            connectBtn.disabled = true;
            statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Disconnecting...';
            statusElement.className = 'badge status-connecting connection-pulse';
            
            const response = await fetch('/api/connection/disconnect', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showToast('Success', 'Disconnected from IBKR', 'success');
                updateConnectionStatus(false);
            } else {
                showToast('Error', result.message, 'error');
            }
            
        } catch (error) {
            showToast('Error', 'Failed to disconnect: ' + error.message, 'error');
        } finally {
            connectBtn.disabled = false;
        }
    } else {
        // Connect
        try {
            connectBtn.disabled = true;
            statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Connecting...';
            statusElement.className = 'badge status-connecting connection-pulse';
            
            const formData = {
                host: document.getElementById('host').value,
                port: parseInt(document.getElementById('port').value),
                client_id: parseInt(document.getElementById('client-id').value)
            };
            
            const response = await fetch('/api/connection/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                showToast('Success', 'Connected to IBKR successfully', 'success');
                updateConnectionStatus(true);
            } else {
                showToast('Error', result.message, 'error');
                updateConnectionStatus(false);
            }
            
        } catch (error) {
            showToast('Error', 'Failed to connect: ' + error.message, 'error');
            updateConnectionStatus(false);
        } finally {
            connectBtn.disabled = false;
        }
    }
}

async function showFiles() {
    const modal = new bootstrap.Modal(document.getElementById('filesModal'));
    const loadingElement = document.getElementById('files-loading');
    const listElement = document.getElementById('files-list');
    const emptyElement = document.getElementById('files-empty');
    const tbody = document.getElementById('files-tbody');
    
    // Show modal and loading state
    modal.show();
    loadingElement.style.display = 'block';
    listElement.style.display = 'none';
    emptyElement.style.display = 'none';
    
    try {
        const response = await fetch('/api/files');
        const result = await response.json();
        
        loadingElement.style.display = 'none';
        
        if (result.success && result.files.length > 0) {
            // Populate files table
            tbody.innerHTML = '';
            result.files.forEach(file => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${file.filename}</td>
                    <td class="file-size">${formatFileSize(file.size)}</td>
                    <td>${new Date(file.modified).toLocaleString()}</td>
                    <td>
                        <a href="/api/files/${file.filename}" class="btn btn-sm btn-outline-primary" download>
                            <i class="fas fa-download me-1"></i>Download
                        </a>
                    </td>
                `;
                tbody.appendChild(row);
            });
            listElement.style.display = 'block';
        } else {
            emptyElement.style.display = 'block';
        }
        
    } catch (error) {
        loadingElement.style.display = 'none';
        showToast('Error', 'Failed to load files: ' + error.message, 'error');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastIcon = document.getElementById('toast-icon');
    const toastTitle = document.getElementById('toast-title');
    const toastBody = document.getElementById('toast-body');
    
    // Set icon and styling based on type
    let iconClass = 'fas fa-info-circle';
    let headerClass = 'toast-header';
    
    switch (type) {
        case 'success':
            iconClass = 'fas fa-check-circle text-success';
            break;
        case 'error':
            iconClass = 'fas fa-exclamation-circle text-danger';
            break;
        case 'warning':
            iconClass = 'fas fa-exclamation-triangle text-warning';
            break;
    }
    
    toastIcon.className = iconClass;
    toastTitle.textContent = title;
    toastBody.textContent = message;
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Utility functions
function validateSymbol(symbol) {
    return /^[A-Za-z0-9.-]+$/.test(symbol.trim());
}

function validateSymbols(symbolsText) {
    const symbols = symbolsText.split(',').map(s => s.trim()).filter(s => s);
    const invalid = symbols.filter(s => !validateSymbol(s));
    return {
        valid: invalid.length === 0,
        symbols: symbols,
        invalid: invalid
    };
}

function showApiDocs() {
    const apiDocsContent = `
    <div class="api-docs">
        <h3>IBKR Data Downloader API Reference</h3>
        
        <h4>Connection Endpoints</h4>
        <div class="endpoint">
            <code>GET /api/connection/status</code> - Get connection status<br>
            <code>POST /api/connection/connect</code> - Connect to IBKR<br>
            <code>POST /api/connection/disconnect</code> - Disconnect from IBKR
        </div>
        
        <h4>Historical Data Endpoints</h4>
        <div class="endpoint">
            <code>POST /api/download/single</code> - Download single symbol<br>
            <code>POST /api/download/multiple</code> - Download multiple symbols<br>
            <code>GET /api/download/status</code> - Get download progress
        </div>
        
        <h4>Real-Time Streaming Endpoints</h4>
        <div class="endpoint">
            <code>POST /api/streaming/start</code> - Start real-time stream<br>
            <code>POST /api/streaming/stop</code> - Stop real-time stream<br>
            <code>GET /api/streaming/data/{req_id}</code> - Get streaming data<br>
            <code>GET /api/streaming/dashboard</code> - Get streaming dashboard<br>
            <code>GET /api/streaming/chart/{req_id}</code> - Get chart data<br>
            <code>GET /api/streaming/export/{req_id}</code> - Export streaming data
        </div>
        
        <h4>News Data Endpoints</h4>
        <div class="endpoint">
            <code>GET /api/news/providers</code> - Get available news providers<br>
            <code>POST /api/news/request</code> - Request historical news<br>
            <code>GET /api/news/data/{req_id}</code> - Get news data<br>
            <code>GET /api/news/search/{req_id}</code> - Search news headlines<br>
            <code>GET /api/news/chart/{req_id}</code> - Get news chart data<br>
            <code>GET /api/news/export/{req_id}</code> - Export news data
        </div>
        
        <h4>File Management Endpoints</h4>
        <div class="endpoint">
            <code>GET /api/files</code> - List data files<br>
            <code>GET /api/files/{filename}</code> - Download specific file
        </div>
        
        <h4>Example Usage</h4>
        <pre><code>
// Connect to IBKR
fetch('/api/connection/connect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        host: '127.0.0.1',
        port: 7497,
        client_id: 1
    })
});

// Download historical data
fetch('/api/download/single', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        symbol: 'AAPL',
        duration: '1 Y',
        bar_size: '1 day'
    })
});

// Start real-time streaming
fetch('/api/streaming/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        symbol: 'AAPL',
        sec_type: 'STK'
    })
});
        </code></pre>
    </div>
    `;
    
    // Create and show modal with API docs
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">API Documentation</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    ${apiDocsContent}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Clean up modal after it's hidden
    modal.addEventListener('hidden.bs.modal', () => {
        document.body.removeChild(modal);
    });
}
