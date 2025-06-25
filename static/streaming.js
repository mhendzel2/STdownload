// Real-time streaming functionality
let activeStreams = new Map();
let dashboardUpdateInterval = null;
let priceChart = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeStreamingPage();
});

function initializeStreamingPage() {
    // Set up streaming form
    const streamingForm = document.getElementById('streaming-form');
    if (streamingForm) {
        streamingForm.addEventListener('submit', handleStartStream);
    }
    
    // Start dashboard updates
    startDashboardUpdates();
    
    // Initial dashboard load
    updateDashboard();
}

function startDashboardUpdates() {
    // Update dashboard every 2 seconds
    dashboardUpdateInterval = setInterval(updateDashboard, 2000);
}

function stopDashboardUpdates() {
    if (dashboardUpdateInterval) {
        clearInterval(dashboardUpdateInterval);
        dashboardUpdateInterval = null;
    }
}

async function handleStartStream(event) {
    event.preventDefault();
    
    if (!app.connected) {
        showToast('Error', 'Not connected to IBKR. Please connect first.', 'error');
        return;
    }
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting...';
        
        const formData = {
            symbol: document.getElementById('stream-symbol').value.trim().toUpperCase(),
            sec_type: document.getElementById('stream-sec-type').value,
            exchange: document.getElementById('stream-exchange').value,
            currency: document.getElementById('stream-currency').value
        };
        
        const response = await fetch('/api/streaming/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Success', result.message, 'success');
            activeStreams.set(result.req_id, {
                symbol: formData.symbol,
                sec_type: formData.sec_type,
                req_id: result.req_id
            });
            
            // Clear form
            document.getElementById('stream-symbol').value = '';
            
            // Update display
            updateActiveStreamsList();
            updateDashboard();
        } else {
            showToast('Error', result.message, 'error');
        }
        
    } catch (error) {
        showToast('Error', 'Failed to start stream: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

async function stopStream(reqId) {
    try {
        const response = await fetch('/api/streaming/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ req_id: reqId })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Success', result.message, 'success');
            activeStreams.delete(reqId);
            updateActiveStreamsList();
            updateDashboard();
        } else {
            showToast('Error', result.message, 'error');
        }
        
    } catch (error) {
        showToast('Error', 'Failed to stop stream: ' + error.message, 'error');
    }
}

async function updateDashboard() {
    try {
        const response = await fetch('/api/streaming/dashboard');
        const result = await response.json();
        
        if (result.success) {
            const dashboard = result.dashboard;
            
            // Update stats
            document.getElementById('total-streams').textContent = dashboard.summary.total_streams;
            document.getElementById('active-streams-count').textContent = dashboard.summary.active_streams;
            document.getElementById('total-data-points').textContent = dashboard.summary.total_data_points.toLocaleString();
            
            const lastUpdate = new Date(dashboard.last_update);
            document.getElementById('last-update').textContent = lastUpdate.toLocaleTimeString();
            
            // Update streams table
            updateStreamsTable(dashboard.streams);
        }
        
    } catch (error) {
        console.error('Failed to update dashboard:', error);
    }
}

function updateStreamsTable(streams) {
    const tbody = document.getElementById('streams-tbody');
    
    if (!streams || streams.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No active streams</td></tr>';
        return;
    }
    
    tbody.innerHTML = '';
    
    streams.forEach(stream => {
        const row = document.createElement('tr');
        
        const priceChange = stream.analytics.price_change || 0;
        const priceChangePct = stream.analytics.price_change_pct || 0;
        const changeClass = priceChange >= 0 ? 'text-success' : 'text-danger';
        const changeIcon = priceChange >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
        
        row.innerHTML = `
            <td><strong>${stream.symbol}</strong></td>
            <td><span class="badge bg-secondary">${stream.sec_type}</span></td>
            <td>${stream.analytics.current_price ? '$' + stream.analytics.current_price.toFixed(2) : '--'}</td>
            <td class="${changeClass}">
                <i class="fas ${changeIcon} me-1"></i>
                ${priceChange.toFixed(2)}
            </td>
            <td class="${changeClass}">
                ${priceChangePct > 0 ? '+' : ''}${priceChangePct.toFixed(2)}%
            </td>
            <td><span class="badge bg-info">${stream.data_points}</span></td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" onclick="showChart(${stream.req_id}, '${stream.symbol}')">
                        <i class="fas fa-chart-line"></i>
                    </button>
                    <button type="button" class="btn btn-outline-success" onclick="exportStreamData(${stream.req_id})">
                        <i class="fas fa-download"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger" onclick="stopStream(${stream.req_id})">
                        <i class="fas fa-stop"></i>
                    </button>
                </div>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function updateActiveStreamsList() {
    const container = document.getElementById('active-streams');
    
    if (activeStreams.size === 0) {
        container.innerHTML = '<p class="text-muted text-center">No active streams</p>';
        return;
    }
    
    let html = '';
    activeStreams.forEach((stream, reqId) => {
        html += `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <strong>${stream.symbol}</strong>
                    <small class="text-muted d-block">${stream.sec_type}</small>
                </div>
                <button class="btn btn-sm btn-outline-danger" onclick="stopStream(${reqId})">
                    <i class="fas fa-stop"></i>
                </button>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function showChart(reqId, symbol) {
    try {
        const response = await fetch(`/api/streaming/chart/${reqId}`);
        const result = await response.json();
        
        if (result.success) {
            displayChart(result.chart_data, symbol);
        } else {
            showToast('Error', 'Failed to load chart data', 'error');
        }
        
    } catch (error) {
        showToast('Error', 'Failed to load chart: ' + error.message, 'error');
    }
}

function displayChart(chartData, symbol) {
    const chartContainer = document.getElementById('chart-container');
    const chartSymbol = document.getElementById('chart-symbol');
    const canvas = document.getElementById('price-chart');
    
    chartSymbol.textContent = symbol;
    chartContainer.style.display = 'block';
    
    // Destroy existing chart
    if (priceChart) {
        priceChart.destroy();
    }
    
    // Prepare data for Chart.js
    const priceData = chartData.price_series.map(point => ({
        x: new Date(point.time),
        y: point.price
    }));
    
    const ctx = canvas.getContext('2d');
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Price',
                data: priceData,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        displayFormats: {
                            second: 'HH:mm:ss',
                            minute: 'HH:mm',
                            hour: 'HH:mm'
                        }
                    }
                },
                y: {
                    beginAtZero: false
                }
            },
            plugins: {
                legend: {
                    display: true
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

async function exportStreamData(reqId) {
    try {
        const response = await fetch(`/api/streaming/export/${reqId}?format=csv`);
        const result = await response.json();
        
        if (result.success) {
            showToast('Success', result.message, 'success');
        } else {
            showToast('Error', result.message, 'error');
        }
        
    } catch (error) {
        showToast('Error', 'Failed to export data: ' + error.message, 'error');
    }
}

function refreshDashboard() {
    updateDashboard();
    showToast('Info', 'Dashboard refreshed', 'info');
}

function showAnalytics() {
    window.location.href = '/analytics';
}

// Cleanup when leaving page
window.addEventListener('beforeunload', function() {
    stopDashboardUpdates();
});