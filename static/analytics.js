// Analytics and visualization functionality
let analyticsCharts = {};
let currentSymbol = null;
let analyticsData = {};

document.addEventListener('DOMContentLoaded', function() {
    initializeAnalyticsPage();
});

function initializeAnalyticsPage() {
    // Load available symbols
    loadAvailableSymbols();
    
    // Set up event listeners
    document.getElementById('analytics-symbol').addEventListener('change', onSymbolChange);
    document.getElementById('chart-type').addEventListener('change', updateAnalytics);
    document.getElementById('time-range').addEventListener('change', updateAnalytics);
    
    // Set up technical indicator checkboxes
    const indicators = ['show-ma', 'show-volume', 'show-volatility', 'show-support-resistance'];
    indicators.forEach(id => {
        document.getElementById(id).addEventListener('change', updateAnalytics);
    });
}

async function loadAvailableSymbols() {
    try {
        const response = await fetch('/api/streaming/dashboard');
        const result = await response.json();
        
        if (result.success) {
            const symbolSelect = document.getElementById('analytics-symbol');
            symbolSelect.innerHTML = '<option value="">Choose a symbol...</option>';
            
            result.dashboard.streams.forEach(stream => {
                const option = document.createElement('option');
                option.value = stream.req_id;
                option.textContent = `${stream.symbol} (${stream.sec_type})`;
                symbolSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load symbols:', error);
    }
}

function onSymbolChange(event) {
    const reqId = event.target.value;
    if (reqId) {
        currentSymbol = reqId;
        updateAnalytics();
    } else {
        clearAnalytics();
    }
}

async function updateAnalytics() {
    if (!currentSymbol) {
        return;
    }
    
    try {
        const response = await fetch(`/api/streaming/data/${currentSymbol}`);
        const result = await response.json();
        
        if (result.success) {
            analyticsData = result;
            updateSummary(result.analytics);
            updateCharts(result.data, result.analytics);
            updateMovingAveragesTable(result.analytics);
            updateMarketStatistics(result.analytics);
            updateTechnicalSignals(result.analytics);
        }
    } catch (error) {
        console.error('Failed to update analytics:', error);
        showToast('Error', 'Failed to load analytics data', 'error');
    }
}

function updateSummary(analytics) {
    document.getElementById('current-price').textContent = 
        analytics.current_price ? '$' + analytics.current_price.toFixed(2) : '--';
    
    const priceChange = analytics.price_change || 0;
    const changeElement = document.getElementById('price-change');
    changeElement.textContent = priceChange >= 0 ? '+$' + priceChange.toFixed(2) : '-$' + Math.abs(priceChange).toFixed(2);
    changeElement.className = priceChange >= 0 ? 'text-success' : 'text-danger';
    
    document.getElementById('volatility').textContent = 
        analytics.volatility ? analytics.volatility.toFixed(4) : '--';
    
    document.getElementById('volume').textContent = 
        analytics.total_volume ? analytics.total_volume.toLocaleString() : '--';
}

function updateCharts(data, analytics) {
    updatePriceChart(data, analytics);
    updateVolumeChart(data);
}

function updatePriceChart(data, analytics) {
    const canvas = document.getElementById('price-analysis-chart');
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart
    if (analyticsCharts.price) {
        analyticsCharts.price.destroy();
    }
    
    // Filter price data
    const priceData = data.filter(tick => tick.price && tick.price > 0)
        .map(tick => ({
            x: new Date(tick.timestamp),
            y: tick.price
        }));
    
    const datasets = [{
        label: 'Price',
        data: priceData,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.1)',
        tension: 0.1,
        fill: document.getElementById('chart-type').value === 'area'
    }];
    
    // Add moving averages if enabled
    if (document.getElementById('show-ma').checked && analytics.moving_averages) {
        Object.entries(analytics.moving_averages).forEach(([period, value], index) => {
            const colors = ['rgb(255, 99, 132)', 'rgb(255, 159, 64)', 'rgb(153, 102, 255)'];
            datasets.push({
                label: `MA ${period.replace('ma_', '')}`,
                data: priceData.map(point => ({ x: point.x, y: value })),
                borderColor: colors[index % colors.length],
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0
            });
        });
    }
    
    analyticsCharts.price = new Chart(ctx, {
        type: 'line',
        data: { datasets },
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
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Price ($)'
                    }
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

function updateVolumeChart(data) {
    const canvas = document.getElementById('volume-analysis-chart');
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart
    if (analyticsCharts.volume) {
        analyticsCharts.volume.destroy();
    }
    
    // Filter volume data
    const volumeData = data.filter(tick => tick.size && tick.size > 0)
        .map(tick => ({
            x: new Date(tick.timestamp),
            y: tick.size
        }));
    
    analyticsCharts.volume = new Chart(ctx, {
        type: 'bar',
        data: {
            datasets: [{
                label: 'Volume',
                data: volumeData,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgb(54, 162, 235)',
                borderWidth: 1
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
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Volume'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true
                }
            }
        }
    });
}

function updateMovingAveragesTable(analytics) {
    const tbody = document.getElementById('ma-table');
    
    if (!analytics.moving_averages || Object.keys(analytics.moving_averages).length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No moving averages available</td></tr>';
        return;
    }
    
    tbody.innerHTML = '';
    
    Object.entries(analytics.moving_averages).forEach(([period, value]) => {
        const periodNum = period.replace('ma_', '');
        const currentPrice = analytics.current_price || 0;
        const difference = currentPrice - value;
        const signal = difference > 0 ? 'Above' : 'Below';
        const signalClass = difference > 0 ? 'text-success' : 'text-danger';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>MA ${periodNum}</td>
            <td>$${value.toFixed(2)}</td>
            <td class="${signalClass}">${difference >= 0 ? '+' : ''}$${difference.toFixed(2)}</td>
            <td><span class="badge ${difference > 0 ? 'bg-success' : 'bg-danger'}">${signal}</span></td>
        `;
        tbody.appendChild(row);
    });
}

function updateMarketStatistics(analytics) {
    document.getElementById('stat-high').textContent = 
        analytics.high_price ? '$' + analytics.high_price.toFixed(2) : '--';
    
    document.getElementById('stat-low').textContent = 
        analytics.low_price ? '$' + analytics.low_price.toFixed(2) : '--';
    
    document.getElementById('stat-range').textContent = 
        analytics.price_range ? '$' + analytics.price_range.toFixed(2) : '--';
    
    const avgPrice = analytics.high_price && analytics.low_price ? 
        (analytics.high_price + analytics.low_price) / 2 : null;
    document.getElementById('stat-avg').textContent = 
        avgPrice ? '$' + avgPrice.toFixed(2) : '--';
    
    document.getElementById('stat-points').textContent = 
        analytics.data_points ? analytics.data_points.toLocaleString() : '--';
}

function updateTechnicalSignals(analytics) {
    const container = document.getElementById('technical-signals');
    
    let signals = [];
    
    // Moving average signals
    if (analytics.moving_averages && analytics.current_price) {
        const currentPrice = analytics.current_price;
        Object.entries(analytics.moving_averages).forEach(([period, ma]) => {
            const signal = currentPrice > ma ? 'Bullish' : 'Bearish';
            const signalClass = currentPrice > ma ? 'success' : 'danger';
            signals.push({
                indicator: `MA ${period.replace('ma_', '')}`,
                signal: signal,
                class: signalClass
            });
        });
    }
    
    // Volatility signal
    if (analytics.volatility) {
        const volatility = analytics.volatility;
        let signal, signalClass;
        if (volatility > 0.02) {
            signal = 'High Volatility';
            signalClass = 'warning';
        } else if (volatility < 0.005) {
            signal = 'Low Volatility';
            signalClass = 'info';
        } else {
            signal = 'Normal Volatility';
            signalClass = 'secondary';
        }
        
        signals.push({
            indicator: 'Volatility',
            signal: signal,
            class: signalClass
        });
    }
    
    if (signals.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No technical signals available yet
            </div>
        `;
        return;
    }
    
    let html = '';
    signals.forEach(signal => {
        html += `
            <div class="alert alert-${signal.class} py-2 mb-2">
                <strong>${signal.indicator}:</strong> ${signal.signal}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function clearAnalytics() {
    // Clear summary
    document.getElementById('current-price').textContent = '--';
    document.getElementById('price-change').textContent = '--';
    document.getElementById('volatility').textContent = '--';
    document.getElementById('volume').textContent = '--';
    
    // Clear charts
    Object.values(analyticsCharts).forEach(chart => {
        if (chart) chart.destroy();
    });
    analyticsCharts = {};
    
    // Clear tables
    document.getElementById('ma-table').innerHTML = 
        '<tr><td colspan="4" class="text-center text-muted">No data available</td></tr>';
    
    // Clear statistics
    ['stat-high', 'stat-low', 'stat-range', 'stat-avg', 'stat-points'].forEach(id => {
        document.getElementById(id).textContent = '--';
    });
    
    // Clear signals
    document.getElementById('technical-signals').innerHTML = `
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            Select a symbol to view technical signals
        </div>
    `;
}

function exportChart(chartType) {
    if (analyticsCharts[chartType]) {
        const url = analyticsCharts[chartType].toBase64Image();
        const link = document.createElement('a');
        link.download = `${chartType}_chart.png`;
        link.href = url;
        link.click();
        showToast('Success', 'Chart exported successfully', 'success');
    }
}

function fullScreenChart(chartType) {
    const modal = new bootstrap.Modal(document.getElementById('chartModal'));
    modal.show();
    
    // Clone chart to fullscreen canvas
    setTimeout(() => {
        const fullscreenCanvas = document.getElementById('fullscreen-chart');
        const ctx = fullscreenCanvas.getContext('2d');
        
        if (analyticsCharts[chartType]) {
            const config = analyticsCharts[chartType].config;
            new Chart(ctx, config);
        }
    }, 300);
}