// News functionality
let currentNewsReqId = null;
let newsCharts = {};
let newsData = [];

document.addEventListener('DOMContentLoaded', function() {
    initializeNewsPage();
});

function initializeNewsPage() {
    // Set up news form
    const newsForm = document.getElementById('news-form');
    if (newsForm) {
        newsForm.addEventListener('submit', handleNewsRequest);
    }
    
    // Set up search
    document.getElementById('search-keyword').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchNews();
        }
    });
    
    // Load news providers on page load
    setTimeout(loadNewsProviders, 1000);
}

async function loadNewsProviders() {
    if (!app.connected) {
        showToast('Error', 'Not connected to IBKR. Please connect first.', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/news/providers');
        const result = await response.json();
        
        if (result.success) {
            const select = document.getElementById('news-providers');
            select.innerHTML = '<option value="">All Providers</option>';
            
            result.providers.forEach(provider => {
                const option = document.createElement('option');
                option.value = provider.code;
                option.textContent = `${provider.name} (${provider.code})`;
                select.appendChild(option);
            });
            
            showToast('Success', `Loaded ${result.providers.length} news providers`, 'success');
        } else {
            showToast('Error', result.message, 'error');
        }
    } catch (error) {
        showToast('Error', 'Failed to load news providers: ' + error.message, 'error');
    }
}

async function handleNewsRequest(event) {
    event.preventDefault();
    
    if (!app.connected) {
        showToast('Error', 'Not connected to IBKR. Please connect first.', 'error');
        return;
    }
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Requesting...';
        
        // Get selected providers
        const providersSelect = document.getElementById('news-providers');
        const selectedProviders = Array.from(providersSelect.selectedOptions)
            .map(option => option.value)
            .filter(value => value)
            .join(',');
        
        // Format dates
        const startDate = document.getElementById('news-start-date').value;
        const endDate = document.getElementById('news-end-date').value;
        
        const formData = {
            symbol: document.getElementById('news-symbol').value.trim().toUpperCase(),
            con_id: document.getElementById('news-con-id').value || null,
            provider_codes: selectedProviders,
            start_date: startDate ? formatDateForAPI(startDate) : '',
            end_date: endDate ? formatDateForAPI(endDate) : '',
            total_results: parseInt(document.getElementById('news-total-results').value) || 10
        };
        
        const response = await fetch('/api/news/request', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Success', result.message, 'success');
            currentNewsReqId = result.req_id;
            newsData = result.news_data;
            
            displayNewsData(result.news_data);
            updateNewsSummary(result.summary);
            
            // Load charts if data available
            if (result.news_data.length > 0) {
                loadNewsCharts();
            }
        } else {
            showToast('Error', result.message, 'error');
        }
        
    } catch (error) {
        showToast('Error', 'Failed to request news: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

function formatDateForAPI(dateTimeLocal) {
    // Convert from 'YYYY-MM-DDTHH:mm' to 'YYYY-MM-DD HH:mm:ss'
    return dateTimeLocal.replace('T', ' ') + ':00';
}

function displayNewsData(news) {
    const container = document.getElementById('news-headlines');
    
    if (!news || news.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-newspaper fa-3x mb-3"></i>
                <p>No news headlines found for the specified criteria.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    news.forEach((item, index) => {
        const timestamp = new Date(item.timestamp).toLocaleString();
        const receivedAt = new Date(item.received_at).toLocaleString();
        
        html += `
            <div class="news-item border-bottom py-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-2">${item.headline}</h6>
                        <div class="d-flex flex-wrap gap-2 mb-2">
                            <span class="badge bg-primary">${item.provider_code}</span>
                            <span class="badge bg-secondary">${timestamp}</span>
                            <span class="badge bg-info">ID: ${item.article_id}</span>
                        </div>
                        <small class="text-muted">Received: ${receivedAt}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-light text-dark">#${index + 1}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function updateNewsSummary(summary) {
    if (!summary) return;
    
    document.getElementById('total-news').textContent = summary.total_items || 0;
    document.getElementById('news-providers-count').textContent = summary.providers ? summary.providers.length : 0;
    
    if (summary.date_range && summary.date_range.earliest && summary.date_range.latest) {
        const earliest = new Date(summary.date_range.earliest).toLocaleDateString();
        const latest = new Date(summary.date_range.latest).toLocaleDateString();
        document.getElementById('news-date-range').textContent = earliest === latest ? earliest : `${earliest} - ${latest}`;
    } else {
        document.getElementById('news-date-range').textContent = '--';
    }
    
    document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
}

async function searchNews() {
    if (!currentNewsReqId) {
        showToast('Error', 'No news data loaded. Please request news first.', 'error');
        return;
    }
    
    const keyword = document.getElementById('search-keyword').value.trim();
    if (!keyword) {
        showToast('Error', 'Please enter a search keyword', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/news/search/${currentNewsReqId}?keyword=${encodeURIComponent(keyword)}`);
        const result = await response.json();
        
        if (result.success) {
            displaySearchResults(result.results, result.keyword);
            showToast('Success', `Found ${result.total_found} headlines containing "${keyword}"`, 'success');
        } else {
            showToast('Error', result.message, 'error');
        }
    } catch (error) {
        showToast('Error', 'Search failed: ' + error.message, 'error');
    }
}

function displaySearchResults(results, keyword) {
    const container = document.getElementById('search-results');
    
    if (!results || results.length === 0) {
        container.innerHTML = `<div class="alert alert-info mt-2">No headlines found containing "${keyword}"</div>`;
        container.style.display = 'block';
        return;
    }
    
    let html = `<div class="alert alert-success mt-2">Found ${results.length} headlines:</div>`;
    
    results.forEach((item, index) => {
        const timestamp = new Date(item.timestamp).toLocaleString();
        // Highlight the keyword in the headline
        const highlightedHeadline = item.headline.replace(
            new RegExp(keyword, 'gi'),
            `<mark>$&</mark>`
        );
        
        html += `
            <div class="border p-2 mb-2 rounded">
                <div class="small">${highlightedHeadline}</div>
                <div class="d-flex gap-1 mt-1">
                    <span class="badge bg-primary">${item.provider_code}</span>
                    <span class="badge bg-secondary">${timestamp}</span>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    container.style.display = 'block';
}

async function loadNewsCharts() {
    if (!currentNewsReqId) return;
    
    try {
        const response = await fetch(`/api/news/chart/${currentNewsReqId}`);
        const result = await response.json();
        
        if (result.success) {
            showNewsCharts();
            displayProviderChart(result.chart_data);
            displayTimeChart(result.chart_data);
            displaySentimentAnalysis(result.sentiment_data);
        }
    } catch (error) {
        console.error('Failed to load news charts:', error);
    }
}

function showNewsCharts() {
    document.getElementById('news-charts').style.display = 'block';
    document.getElementById('sentiment-analysis').style.display = 'block';
}

function displayProviderChart(chartData) {
    const canvas = document.getElementById('provider-chart');
    const ctx = canvas.getContext('2d');
    
    if (newsCharts.provider) {
        newsCharts.provider.destroy();
    }
    
    if (!chartData.provider_distribution || chartData.provider_distribution.labels.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No provider data available', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    newsCharts.provider = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: chartData.provider_distribution.labels,
            datasets: [{
                data: chartData.provider_distribution.data,
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function displayTimeChart(chartData) {
    const canvas = document.getElementById('time-chart');
    const ctx = canvas.getContext('2d');
    
    if (newsCharts.time) {
        newsCharts.time.destroy();
    }
    
    if (!chartData.time_distribution || chartData.time_distribution.labels.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No time data available', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    newsCharts.time = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.time_distribution.labels,
            datasets: [{
                label: 'News Count',
                data: chartData.time_distribution.data,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgb(54, 162, 235)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function displaySentimentAnalysis(sentimentData) {
    if (!sentimentData || !sentimentData.sentiment_distribution) {
        return;
    }
    
    const canvas = document.getElementById('sentiment-chart');
    const ctx = canvas.getContext('2d');
    
    if (newsCharts.sentiment) {
        newsCharts.sentiment.destroy();
    }
    
    const distribution = sentimentData.sentiment_distribution;
    
    newsCharts.sentiment = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Positive', 'Negative', 'Neutral'],
            datasets: [{
                data: [distribution.positive, distribution.negative, distribution.neutral],
                backgroundColor: ['#28a745', '#dc3545', '#6c757d']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
    
    // Display sentiment breakdown
    const breakdown = document.getElementById('sentiment-breakdown');
    let html = '<h6>Sentiment Breakdown</h6>';
    
    const sentiments = ['positive', 'negative', 'neutral'];
    sentiments.forEach(sentiment => {
        const count = distribution[sentiment];
        const percentage = sentimentData.total_analyzed > 0 ? 
            ((count / sentimentData.total_analyzed) * 100).toFixed(1) : 0;
        
        const badgeClass = sentiment === 'positive' ? 'success' : 
                          sentiment === 'negative' ? 'danger' : 'secondary';
        
        html += `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="text-capitalize">${sentiment}:</span>
                <div>
                    <span class="badge bg-${badgeClass}">${count} (${percentage}%)</span>
                </div>
            </div>
        `;
    });
    
    breakdown.innerHTML = html;
}

async function exportNews() {
    if (!currentNewsReqId) {
        showToast('Error', 'No news data to export', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/news/export/${currentNewsReqId}?format=csv`);
        const result = await response.json();
        
        if (result.success) {
            showToast('Success', result.message, 'success');
        } else {
            showToast('Error', result.message, 'error');
        }
    } catch (error) {
        showToast('Error', 'Export failed: ' + error.message, 'error');
    }
}