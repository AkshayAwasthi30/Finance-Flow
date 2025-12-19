// Finance Flow Application - Complete Working Version
class FinanceFlowApp {
    constructor() {
        this.currentTaskId = null;
        this.pollInterval = null;
        this.transactionData = null;
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupDateInputs();
        console.log('Finance Flow App initialized');
    }
    
    bindEvents() {
        // Authentication form
        const authForm = document.getElementById('auth-form');
        if (authForm) {
            authForm.addEventListener('submit', this.handleAuthentication.bind(this));
            console.log('Auth form bound');
        }
        
        // Processing form
        const processingForm = document.getElementById('processing-form');
        if (processingForm) {
            processingForm.addEventListener('submit', this.handleProcessing.bind(this));
            console.log('Processing form bound');
        }
        
        // Navigation buttons
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.refreshData.bind(this));
        }
        
        const exportBtn = document.getElementById('export-data');
        if (exportBtn) {
            exportBtn.addEventListener('click', this.exportData.bind(this));
        }
    }
    
    setupDateInputs() {
        const fromDate = document.getElementById('from-date');
        const toDate = document.getElementById('to-date');
        
        if (fromDate && toDate) {
            const today = new Date();
            const oneYearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
            
            fromDate.value = oneYearAgo.toISOString().split('T')[0];
            toDate.value = today.toISOString().split('T')[0];
            
            console.log('Date inputs set up');
        }
    }
    
    async handleAuthentication(event) {
        event.preventDefault();
        console.log('Authentication form submitted');
        
        const form = event.target;
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        
        // Show loading
        this.showButtonLoading(submitBtn, true);
        
        try {
            const response = await fetch('/authenticate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: formData.get('email'),
                    password: formData.get('password')
                })
            });
            
            const result = await response.json();
            console.log('Auth response:', result);
            
            if (result.success) {
                this.showToast('Authentication successful! Redirecting...', 'success');
                
                // Wait a moment for the toast to show, then redirect
                setTimeout(() => {
                    window.location.href = result.redirect || '/dashboard';
                }, 1500);
            } else {
                this.showToast(result.message || 'Authentication failed', 'error');
            }
        } catch (error) {
            console.error('Auth error:', error);
            this.showToast('Network error. Please try again.', 'error');
        } finally {
            this.showButtonLoading(submitBtn, false);
        }
    }
    
    async handleProcessing(event) {
        event.preventDefault();
        console.log('Processing form submitted');
        
        const form = event.target;
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        
        // Validate form data
        const fromDate = formData.get('from_date');
        const toDate = formData.get('to_date');
        const pdfPassword = formData.get('pdf_password');
        
        if (!fromDate || !toDate || !pdfPassword) {
            this.showToast('Please fill in all required fields', 'warning');
            return;
        }
        
        // Show loading
        this.showButtonLoading(submitBtn, true);
        
        try {
            const response = await fetch('/api/process-statements', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_date: fromDate,
                    to_date: toDate,
                    pdf_password: pdfPassword
                })
            });
            
            const result = await response.json();
            console.log('Processing response:', result);
            
            if (result.success) {
                this.currentTaskId = result.task_id;
                this.showToast('Processing started successfully!', 'success');
                this.showLoadingOverlay();
                this.startProgressPolling();
                this.hideSetupSection();
            } else {
                this.showToast(result.message || 'Processing failed to start', 'error');
            }
        } catch (error) {
            console.error('Processing error:', error);
            this.showToast('Network error. Please try again.', 'error');
        } finally {
            this.showButtonLoading(submitBtn, false);
        }
    }
    
    showButtonLoading(button, isLoading) {
        if (isLoading) {
            button.disabled = true;
            const btnContent = button.querySelector('.btn-content');
            if (btnContent) {
                const originalHTML = btnContent.innerHTML;
                button.dataset.originalHTML = originalHTML;
                
                btnContent.innerHTML = `
                    <div class="btn-icon">
                        <div class="loader-spinner"></div>
                    </div>
                    <div class="btn-text">
                        <span class="btn-title">Processing...</span>
                        <span class="btn-subtitle">Please wait</span>
                    </div>
                `;
            }
        } else {
            button.disabled = false;
            const btnContent = button.querySelector('.btn-content');
            if (btnContent && button.dataset.originalHTML) {
                btnContent.innerHTML = button.dataset.originalHTML;
            }
        }
    }
    
    showLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            console.log('Loading overlay shown');
        }
    }
    
    hideLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
            console.log('Loading overlay hidden');
        }
    }
    
    startProgressPolling() {
        const messages = [
            '🔐 Establishing secure connection...',
            '📧 Scanning Gmail inbox...',
            '📄 Extracting PDF attachments...',
            '🔓 Decrypting bank statements...',
            '💳 Processing transactions...',
            '🏷️ Categorizing expenses intelligently...',
            '📊 Analyzing spending patterns...',
            '🧠 Generating AI insights...',
            '✨ Finalizing your dashboard...'
        ];
        
        let messageIndex = 0;
        let pollCount = 0;
        
        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/processing-status/${this.currentTaskId}`);
                const status = await response.json();
                
                console.log('Progress update:', status);
                pollCount++;
                
                // Update message based on progress
                if (status.progress > messageIndex * 11 && messageIndex < messages.length - 1) {
                    messageIndex++;
                    this.updateLoadingStep(messageIndex);
                }
                
                this.updateProgress({
                    ...status,
                    message: messages[messageIndex] || status.message || 'Processing...'
                });
                
                if (status.status === 'completed') {
                    clearInterval(this.pollInterval);
                    this.updateProgress({ progress: 100, message: '✅ Processing completed!' });
                    
                    setTimeout(async () => {
                        await this.loadDashboardData();
                        this.hideLoadingOverlay();
                        this.showDashboard();
                        this.showToast('Analysis completed successfully! 🎉', 'success');
                    }, 2000);
                    
                } else if (status.status === 'error') {
                    clearInterval(this.pollInterval);
                    this.hideLoadingOverlay();
                    this.showToast(status.message || 'Processing failed', 'error');
                }
                
                // Timeout after 2 minutes
                if (pollCount > 60) {
                    clearInterval(this.pollInterval);
                    this.hideLoadingOverlay();
                    this.showToast('Processing is taking longer than expected. Please try again.', 'warning');
                }
                
            } catch (error) {
                console.error('Progress polling error:', error);
                // Continue polling even if there's an error, but limit attempts
                if (pollCount > 30) {
                    clearInterval(this.pollInterval);
                    this.hideLoadingOverlay();
                    this.showToast('Unable to check processing status. Please refresh and try again.', 'error');
                }
            }
        }, 2000);
    }
    
    updateProgress(status) {
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const loadingMessage = document.getElementById('loading-message');
        
        if (progressBar) {
            progressBar.style.width = `${status.progress || 0}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${status.progress || 0}%`;
        }
        
        if (loadingMessage) {
            loadingMessage.textContent = status.message || 'Processing...';
        }
    }
    
    updateLoadingStep(stepIndex) {
        const steps = document.querySelectorAll('.loading-step');
        steps.forEach((step, index) => {
            if (index === stepIndex) {
                step.classList.add('active');
            } else if (index < stepIndex) {
                step.classList.remove('active');
                step.style.opacity = '0.6';
            } else {
                step.classList.remove('active');
            }
        });
    }
    
    async loadDashboardData() {
        try {
            console.log('Loading dashboard data...');
            const response = await fetch(`/api/transactions/${this.currentTaskId}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.transactionData = data;
            console.log('Dashboard data loaded:', this.transactionData);
            
            // Update dashboard with real data
            this.updateDashboardContent();
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showToast('Error loading dashboard data', 'error');
        }
    }
    
    updateDashboardContent() {
        const dashboardContent = document.getElementById('dashboard-content');
        if (dashboardContent) {
            dashboardContent.innerHTML = `
                <div class="dashboard-summary">
                    <h2>📊 Financial Analysis Complete</h2>
                    <div class="summary-grid">
                        <div class="summary-card">
                            <h3>Total Transactions</h3>
                            <p class="big-number">${this.transactionData?.summary?.total_transactions || 0}</p>
                        </div>
                        <div class="summary-card">
                            <h3>Total Income</h3>
                            <p class="big-number income">₹${(this.transactionData?.summary?.total_income || 0).toLocaleString('en-IN')}</p>
                        </div>
                        <div class="summary-card">
                            <h3>Total Expenses</h3>
                            <p class="big-number expense">₹${(this.transactionData?.summary?.total_expenses || 0).toLocaleString('en-IN')}</p>
                        </div>
                        <div class="summary-card">
                            <h3>Net Savings</h3>
                            <p class="big-number savings">₹${(this.transactionData?.summary?.net_savings || 0).toLocaleString('en-IN')}</p>
                        </div>
                    </div>
                    
                    <div class="insights-preview">
                        <h3>🧠 AI Insights Preview</h3>
                        <div class="insights-list">
                            ${(this.transactionData?.insights || []).slice(0, 3).map(insight => `
                                <div class="insight-item">
                                    <h4>${insight.title}</h4>
                                    <p>${insight.message}</p>
                                    <span class="insight-badge ${insight.severity}">${insight.severity}</span>
                                </div>
                            `).join('') || '<p>No insights available yet.</p>'}
                        </div>
                    </div>
                    
                    <div class="actions-section">
                        <button onclick="window.financeFlowApp.exportData()" class="btn-secondary">
                            <i class="ri-download-line"></i>
                            Export Data
                        </button>
                        <button onclick="window.location.reload()" class="btn-primary">
                            <i class="ri-refresh-line"></i>
                            New Analysis
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    showDashboard() {
        const setupSection = document.getElementById('setup-section');
        const dashboardContent = document.getElementById('dashboard-content');
        
        if (setupSection && dashboardContent) {
            setupSection.style.display = 'none';
            dashboardContent.classList.remove('hidden');
            dashboardContent.style.display = 'block';
            console.log('Dashboard shown');
        }
    }
    
    hideSetupSection() {
        const setupSection = document.getElementById('setup-section');
        if (setupSection) {
            setupSection.style.opacity = '0.5';
            setupSection.style.pointerEvents = 'none';
        }
    }
    
    showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const iconMap = {
            success: 'ri-check-line',
            error: 'ri-close-line',
            warning: 'ri-error-warning-line',
            info: 'ri-information-line'
        };
        
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-icon">
                    <i class="${iconMap[type] || iconMap.info}"></i>
                </div>
                <div class="toast-text">
                    <div class="toast-message">${message}</div>
                </div>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="ri-close-line"></i>
                </button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Show toast
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
        
        console.log(`Toast shown: ${message}`);
    }
    
    refreshData() {
        this.showToast('Refresh functionality will be implemented in full version', 'info');
    }
    
    exportData() {
        if (!this.transactionData) {
            this.showToast('No data to export', 'warning');
            return;
        }
        
        const dataStr = JSON.stringify(this.transactionData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `finance_flow_data_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        this.showToast('Data exported successfully! 📊', 'success');
    }
}

// Utility Functions
function setDateRange(days) {
    const today = new Date();
    const pastDate = new Date(today.getTime() - (days * 24 * 60 * 60 * 1000));
    
    const fromDateInput = document.getElementById('from-date');
    const toDateInput = document.getElementById('to-date');
    
    if (fromDateInput && toDateInput) {
        fromDateInput.value = pastDate.toISOString().split('T')[0];
        toDateInput.value = today.toISOString().split('T')[0];
        
        // Update active state
        document.querySelectorAll('.quick-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        
        console.log(`Date range set to last ${days} days`);
    }
}

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const toggleBtn = document.querySelector(`#${inputId} + .password-toggle`);
    const icon = toggleBtn?.querySelector('i');
    
    if (input && icon) {
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'ri-eye-off-line';
        } else {
            input.type = 'password';
            icon.className = 'ri-eye-line';
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing app...');
    
    // Initialize the main app
    window.financeFlowApp = new FinanceFlowApp();
    
    // Set default date range
    setTimeout(() => {
        const lastYearBtn = document.querySelector('.quick-btn[onclick*="365"]');
        if (lastYearBtn) {
            lastYearBtn.classList.add('active');
        }
    }, 100);
    
    console.log('App initialization complete');
});
