// Download page specific functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeDownloadPage();
});

function initializeDownloadPage() {
    // Set up form handlers
    const singleForm = document.getElementById('single-download-form');
    const multipleForm = document.getElementById('multiple-download-form');
    
    if (singleForm) {
        singleForm.addEventListener('submit', handleSingleDownload);
    }
    
    if (multipleForm) {
        multipleForm.addEventListener('submit', handleMultipleDownload);
    }
    
    // Set up symbol validation
    const symbolInputs = document.querySelectorAll('#single-symbol, #multiple-symbols');
    symbolInputs.forEach(input => {
        input.addEventListener('input', validateSymbolInput);
    });
    
    // Start status polling for multiple downloads
    setInterval(updateDownloadStatus, 2000);
}

function validateSymbolInput(event) {
    const input = event.target;
    const value = input.value.trim();
    
    if (input.id === 'single-symbol') {
        if (value && !validateSymbol(value)) {
            input.classList.add('is-invalid');
            input.classList.remove('is-valid');
        } else if (value) {
            input.classList.add('is-valid');
            input.classList.remove('is-invalid');
        } else {
            input.classList.remove('is-valid', 'is-invalid');
        }
    } else if (input.id === 'multiple-symbols') {
        if (value) {
            const validation = validateSymbols(value);
            if (validation.valid) {
                input.classList.add('is-valid');
                input.classList.remove('is-invalid');
            } else {
                input.classList.add('is-invalid');
                input.classList.remove('is-valid');
            }
        } else {
            input.classList.remove('is-valid', 'is-invalid');
        }
    }
}

async function handleSingleDownload(event) {
    event.preventDefault();
    
    if (!app.connected) {
        showToast('Error', 'Not connected to IBKR. Please connect first.', 'error');
        return;
    }
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Downloading...';
        
        const formData = {
            symbol: document.getElementById('single-symbol').value.trim().toUpperCase(),
            sec_type: document.getElementById('single-sec-type').value,
            exchange: document.getElementById('single-exchange').value,
            currency: document.getElementById('single-currency').value,
            duration: document.getElementById('single-duration').value,
            bar_size: document.getElementById('single-bar-size').value,
            what_to_show: document.getElementById('single-what-to-show').value,
            use_rth: document.getElementById('single-use-rth').checked
        };
        
        const response = await fetch('/api/download/single', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Success', result.message, 'success');
            displaySingleResult(result);
        } else {
            showToast('Error', result.message, 'error');
        }
        
    } catch (error) {
        showToast('Error', 'Download failed: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

async function handleMultipleDownload(event) {
    event.preventDefault();
    
    if (!app.connected) {
        showToast('Error', 'Not connected to IBKR. Please connect first.', 'error');
        return;
    }
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting Download...';
        
        const formData = {
            symbols: document.getElementById('multiple-symbols').value,
            sec_type: document.getElementById('multiple-sec-type').value,
            exchange: document.getElementById('multiple-exchange').value,
            currency: document.getElementById('multiple-currency').value,
            duration: document.getElementById('multiple-duration').value,
            bar_size: document.getElementById('multiple-bar-size').value,
            what_to_show: document.getElementById('multiple-what-to-show').value,
            use_rth: document.getElementById('multiple-use-rth').checked,
            save_excel: document.getElementById('multiple-save-excel').checked
        };
        
        const response = await fetch('/api/download/multiple', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Success', result.message, 'success');
            app.downloading = true;
            updateDownloadStatus();
        } else {
            showToast('Error', result.message, 'error');
        }
        
    } catch (error) {
        showToast('Error', 'Download failed: ' + error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

async function updateDownloadStatus() {
    if (!app.downloading) return;
    
    try {
        const response = await fetch('/api/download/status');
        const status = await response.json();
        
        const statusElement = document.getElementById('download-status');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        
        if (status.active) {
            statusElement.innerHTML = '<div class="badge bg-primary download-active">Downloading</div>';
            progressContainer.style.display = 'block';
            
            const progress = status.total > 0 ? (status.progress / status.total) * 100 : 0;
            progressBar.style.width = progress + '%';
            progressBar.setAttribute('aria-valuenow', progress);
            
            progressText.textContent = `${status.progress}/${status.total} - ${status.current_symbol}`;
            
        } else if (Object.keys(status.results).length > 0 || status.errors.length > 0) {
            // Download completed
            statusElement.innerHTML = '<div class="badge bg-success">Complete</div>';
            progressContainer.style.display = 'none';
            app.downloading = false;
            
            displayMultipleResults(status);
            
        } else {
            statusElement.innerHTML = '<div class="badge bg-secondary">Ready</div>';
            progressContainer.style.display = 'none';
        }
        
    } catch (error) {
        console.error('Failed to update download status:', error);
    }
}

function displaySingleResult(result) {
    // Could add a results display for single downloads
    console.log('Single download result:', result);
}

function displayMultipleResults(status) {
    const resultsCard = document.getElementById('results-card');
    const resultsContent = document.getElementById('results-content');
    
    if (!resultsCard || !resultsContent) return;
    
    let html = '';
    
    // Success results
    if (Object.keys(status.results).length > 0) {
        html += '<h6><i class="fas fa-check-circle text-success me-2"></i>Successfully Downloaded</h6>';
        html += '<div class="table-responsive">';
        html += '<table class="table table-sm results-table">';
        html += '<thead><tr><th>Symbol</th><th>Records</th><th>Date Range</th><th>File</th></tr></thead>';
        html += '<tbody>';
        
        Object.entries(status.results).forEach(([symbol, summary]) => {
            const startDate = summary.start_date ? new Date(summary.start_date).toLocaleDateString() : 'N/A';
            const endDate = summary.end_date ? new Date(summary.end_date).toLocaleDateString() : 'N/A';
            
            html += `
                <tr>
                    <td><strong>${symbol}</strong></td>
                    <td><span class="badge bg-primary">${summary.records}</span></td>
                    <td>${startDate} - ${endDate}</td>
                    <td>
                        <a href="/api/files/${symbol}_historical_data.csv" class="btn btn-sm btn-outline-primary" download>
                            <i class="fas fa-download me-1"></i>CSV
                        </a>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
    }
    
    // Error results
    if (status.errors.length > 0) {
        html += '<h6 class="mt-3"><i class="fas fa-exclamation-circle text-danger me-2"></i>Errors</h6>';
        html += '<ul class="list-group list-group-flush">';
        
        status.errors.forEach(error => {
            html += `<li class="list-group-item text-danger">${error}</li>`;
        });
        
        html += '</ul>';
    }
    
    // Excel file link
    if (status.excel_file) {
        html += '<div class="mt-3">';
        html += '<h6><i class="fas fa-file-excel text-success me-2"></i>Combined Excel File</h6>';
        html += `<a href="/api/files/${status.excel_file.split('/').pop()}" class="btn btn-success" download>`;
        html += '<i class="fas fa-download me-2"></i>Download Excel File</a>';
        html += '</div>';
    }
    
    resultsContent.innerHTML = html;
    resultsCard.style.display = 'block';
}
