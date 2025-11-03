// Autodialer Application JavaScript
class AutodialerApp {
    constructor() {
        this.currentNumbers = [];
        this.isCallInProgress = false;
        this.callProgressInterval = null;
        this.statsUpdateInterval = null;
        this.currentCallIndex = 0;
        this.totalCalls = 0;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startStatsPolling();
        this.updateNumberCounter();
    }
    
    setupEventListeners() {
        // File upload drag and drop
        const fileUploadArea = document.querySelector('.file-upload-area');
        if (fileUploadArea) {
            fileUploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
            fileUploadArea.addEventListener('drop', this.handleFileDrop.bind(this));
        }
        
        // File input change
        const fileInput = document.getElementById('file-upload');
        if (fileInput) {
            fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        }
        
        // Textarea input for number counting
        const numbersTextarea = document.getElementById('numbers-textarea');
        if (numbersTextarea) {
            numbersTextarea.addEventListener('input', this.updateNumberCounter.bind(this));
        }
        
        // Single number input validation
        const singleNumberInput = document.getElementById('single-number');
        if (singleNumberInput) {
            singleNumberInput.addEventListener('input', this.validateSingleNumber.bind(this));
            singleNumberInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.addSingleNumber();
                }
            });
        }
        
        // AI command input
        const aiCommandInput = document.getElementById('ai-command');
        if (aiCommandInput) {
            aiCommandInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.processCommand();
                }
            });
        }
        
        // Log search and filter
        const logSearch = document.getElementById('log-search');
        if (logSearch) {
            logSearch.addEventListener('input', this.debounce(this.filterLogs.bind(this), 300));
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
    }
    
    // Utility Functions
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    showStatus(message, type = 'success', duration = 5000) {
        const statusDiv = document.getElementById('status');
        if (!statusDiv) return;
        
        statusDiv.textContent = message;
        statusDiv.className = `status-message ${type}`;
        statusDiv.style.display = 'block';
        
        // Auto-hide after duration
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, duration);
    }
    
    validatePhoneNumber(number) {
        // Remove all non-digit characters except +
        const cleaned = number.replace(/[^\d+]/g, '');
        
        // Check for test number format (1800 followed by 7 digits)
        const testPatterns = [
            /^\+911800\d{7}$/,  // +911800XXXXXXX
            /^911800\d{7}$/,    // 911800XXXXXXX  
            /^1800\d{7}$/       // 1800XXXXXXX
        ];
        
        // Check for regular Indian mobile number format (+91 followed by 10 digits)
        const indianPattern = /^\+91[6-9]\d{9}$/;
        
        return testPatterns.some(pattern => pattern.test(cleaned)) || indianPattern.test(cleaned);
    }
    
    formatPhoneNumber(number) {
        const cleaned = number.replace(/[^\d+]/g, '');
        
        // Handle 1800 numbers
        if (cleaned.includes('1800')) {
            if (cleaned.startsWith('+91')) {
                return cleaned; // Already formatted
            } else if (cleaned.startsWith('91')) {
                return '+' + cleaned;
            } else {
                return '+91' + cleaned;
            }
        }
        
        // Handle regular mobile numbers
        if (cleaned.startsWith('+91')) {
            return cleaned;
        } else if (cleaned.startsWith('91')) {
            return '+' + cleaned;
        } else if (cleaned.match(/^[6-9]\d{9}$/)) {
            return '+91' + cleaned;
        }
        
        return cleaned;
    }
    
    extractNumbersFromText(text) {
        const lines = text.split(/[\n,;]/);
        const numbers = [];
        
        lines.forEach(line => {
            const trimmed = line.trim();
            if (trimmed && this.validatePhoneNumber(trimmed)) {
                const formatted = this.formatPhoneNumber(trimmed);
                if (!numbers.includes(formatted)) {
                    numbers.push(formatted);
                }
            }
        });
        
        return numbers;
    }
    
    // Number Management Functions
    updateNumberCounter() {
        const textarea = document.getElementById('numbers-textarea');
        const counter = document.getElementById('number-count');
        
        if (!textarea || !counter) return;
        
        const numbers = this.extractNumbersFromText(textarea.value);
        counter.textContent = numbers.length;
        
        // Update counter color based on count
        if (numbers.length > 0) {
            counter.parentElement.style.background = 'rgba(40, 167, 69, 0.1)';
            counter.parentElement.style.color = '#28a745';
        } else {
            counter.parentElement.style.background = 'rgba(79, 172, 254, 0.1)';
            counter.parentElement.style.color = '#4facfe';
        }
    }
    
    validateSingleNumber() {
        const input = document.getElementById('single-number');
        if (!input) return;
        
        const isValid = this.validatePhoneNumber(input.value);
        
        if (input.value && !isValid) {
            input.style.borderColor = '#dc3545';
            input.style.boxShadow = '0 0 0 3px rgba(220, 53, 69, 0.1)';
        } else {
            input.style.borderColor = '#e9ecef';
            input.style.boxShadow = 'none';
        }
    }
    
    async uploadNumbers() {
        const textarea = document.getElementById('numbers-textarea');
        if (!textarea || !textarea.value.trim()) {
            this.showStatus('Please enter some phone numbers first', 'error');
            return;
        }
        
        const numbers = this.extractNumbersFromText(textarea.value);
        
        if (numbers.length === 0) {
            this.showStatus('No valid phone numbers found. Please check the format.', 'error');
            return;
        }
        
        try {
            const response = await fetch('/upload-numbers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ numbers: numbers })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                const addedCount = result.valid_numbers ? result.valid_numbers.length : 0;
                const duplicateCount = result.duplicates ? result.duplicates.length : 0;
                this.showStatus(`Successfully added ${addedCount} numbers${duplicateCount > 0 ? ` (${duplicateCount} duplicates removed)` : ''}`, 'success');
                textarea.value = '';
                this.updateNumberCounter();
                this.loadCurrentNumbers();
            } else {
                this.showStatus(result.response || result.message || 'Failed to add numbers', 'error');
            }
        } catch (error) {
            console.error('Error uploading numbers:', error);
            this.showStatus('Error uploading numbers. Please try again.', 'error');
        }
    }
    
    async addSingleNumber() {
        const input = document.getElementById('single-number');
        if (!input || !input.value.trim()) {
            this.showStatus('Please enter a phone number', 'error');
            return;
        }
        
        const number = input.value.trim();
        
        if (!this.validatePhoneNumber(number)) {
            this.showStatus('Please enter a valid phone number (+91XXXXXXXXXX or 1800XXXXXXXX)', 'error');
            return;
        }
        
        try {
            const formattedNumber = this.formatPhoneNumber(number);
            const response = await fetch('/upload-numbers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ numbers: [formattedNumber] })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                const addedCount = result.valid_numbers ? result.valid_numbers.length : 0;
                const duplicateCount = result.duplicates ? result.duplicates.length : 0;
                
                if (duplicateCount > 0 && addedCount === 0) {
                    this.showStatus('Number already exists in the list', 'info');
                } else {
                    this.showStatus('Number added successfully', 'success');
                }
                input.value = '';
                this.loadCurrentNumbers();
            } else {
                this.showStatus(result.response || result.message || 'Failed to add number', 'error');
            }
        } catch (error) {
            console.error('Error adding number:', error);
            this.showStatus('Error adding number. Please try again.', 'error');
        }
    }
    
    async removeNumber(number) {
        try {
            const response = await fetch('/remove-number', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ number: number })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.showStatus('Number removed successfully', 'success');
                this.loadCurrentNumbers();
            } else {
                this.showStatus(result.message || 'Failed to remove number', 'error');
            }
        } catch (error) {
            console.error('Error removing number:', error);
            this.showStatus('Error removing number. Please try again.', 'error');
        }
    }
    
    async loadCurrentNumbers() {
        try {
            const response = await fetch('/get-numbers');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.currentNumbers = result.numbers.map(item => item.number || item);
                this.updateNumbersList();
                this.updateCurrentCount();
            }
        } catch (error) {
            console.error('Error loading numbers:', error);
        }
    }
    
    updateNumbersList() {
        const listContainer = document.getElementById('numbers-list');
        if (!listContainer) return;
        
        if (this.currentNumbers.length === 0) {
            listContainer.innerHTML = '<p class="empty-state">No numbers added yet</p>';
            return;
        }
        
        const listHTML = this.currentNumbers.map(number => `
            <div class="number-item">
                <span>${typeof number === 'object' ? number.number : number}</span>
                <button class="remove-number" onclick="app.removeNumber('${typeof number === 'object' ? number.number : number}')">
                    Remove
                </button>
            </div>
        `).join('');
        
        listContainer.innerHTML = listHTML;
    }
    
    updateCurrentCount() {
        const countElement = document.getElementById('current-count');
        if (countElement) {
            countElement.textContent = this.currentNumbers.length;
        }
    }
    
    // File Upload Functions
    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.style.borderColor = '#4facfe';
        e.currentTarget.style.background = 'rgba(79, 172, 254, 0.1)';
    }
    
    handleFileDrop(e) {
        e.preventDefault();
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
        
        // Reset styles
        e.currentTarget.style.borderColor = '#dee2e6';
        e.currentTarget.style.background = '#f8f9fa';
    }
    
    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }
    
    async processFile(file) {
        if (!file.name.match(/\.(txt|csv)$/i)) {
            this.showStatus('Please select a .txt or .csv file', 'error');
            return;
        }
        
        if (file.size > 1024 * 1024) { // 1MB limit
            this.showStatus('File size must be less than 1MB', 'error');
            return;
        }
        
        try {
            const text = await this.readFileAsText(file);
            const numbers = this.extractNumbersFromText(text);
            
            if (numbers.length === 0) {
                this.showStatus('No valid phone numbers found in the file', 'error');
                return;
            }
            
            const response = await fetch('/upload-numbers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ numbers: numbers })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                const addedCount = result.valid_numbers ? result.valid_numbers.length : 0;
                const duplicateCount = result.duplicates ? result.duplicates.length : 0;
                this.showStatus(`Successfully uploaded ${addedCount} numbers from file${duplicateCount > 0 ? ` (${duplicateCount} duplicates removed)` : ''}`, 'success');
                this.loadCurrentNumbers();
            } else {
                this.showStatus(result.response || result.message || 'Failed to upload file', 'error');
            }
        } catch (error) {
            console.error('Error processing file:', error);
            this.showStatus('Error processing file. Please try again.', 'error');
        }
    }
    
    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = e => resolve(e.target.result);
            reader.onerror = reject;
            reader.readAsText(file);
        });
    }
    
    // AI Command Functions
    async processCommand() {
        const input = document.getElementById('ai-command');
        if (!input || !input.value.trim()) {
            this.showStatus('Please enter a command', 'error');
            return;
        }
        
        const command = input.value.trim();
        
        try {
            const response = await fetch('/ai-command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command: command })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.showStatus(result.response || result.message || 'Command executed successfully', 'success');
                
                // Handle specific actions based on execution result
                if (result.execution_result && result.execution_result.action === 'call_all') {
                    this.startCalling();
                } else if (result.execution_result && result.execution_result.action === 'view_logs') {
                    this.loadCallLogs();
                } else if (result.execution_result && (result.execution_result.action === 'add_number' || result.execution_result.action === 'remove_number')) {
                    this.loadCurrentNumbers();
                }
                
                input.value = '';
            } else {
                this.showStatus(result.response || result.message || 'Command not understood', 'error');
            }
        } catch (error) {
            console.error('Error processing command:', error);
            this.showStatus('Error processing command. Please try again.', 'error');
        }
    }
    
    setCommand(command) {
        const input = document.getElementById('ai-command');
        if (input) {
            input.value = command;
            input.focus();
        }
    }
    
    quickCommand(command) {
        const input = document.getElementById('ai-command');
        if (input) {
            input.value = command;
            this.processCommand();
        }
    }
    
    // Call Control Functions
    async startCalling() {
        if (this.isCallInProgress) {
            this.showStatus('Calling is already in progress', 'info');
            return;
        }
        
        if (this.currentNumbers.length === 0) {
            this.showStatus('No numbers to call. Please add some numbers first.', 'error');
            return;
        }
        
        try {
            const response = await fetch('/start-calling', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.isCallInProgress = true;
                this.totalCalls = this.currentNumbers.length;
                this.currentCallIndex = 0;
                
                this.updateCallControlUI();
                this.startCallProgressPolling();
                this.showStatus('Calling started successfully', 'success');
            } else {
                this.showStatus(result.message || 'Failed to start calling', 'error');
            }
        } catch (error) {
            console.error('Error starting calls:', error);
            this.showStatus('Error starting calls. Please try again.', 'error');
        }
    }
    
    async stopCalling() {
        if (!this.isCallInProgress) {
            this.showStatus('No calling in progress', 'info');
            return;
        }
        
        try {
            const response = await fetch('/stop-calling', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.isCallInProgress = false;
                this.stopCallProgressPolling();
                this.updateCallControlUI();
                this.showStatus('Calling stopped successfully', 'success');
            } else {
                this.showStatus(result.message || 'Failed to stop calling', 'error');
            }
        } catch (error) {
            console.error('Error stopping calls:', error);
            this.showStatus('Error stopping calls. Please try again.', 'error');
        }
    }
    
    updateCallControlUI() {
        const startBtn = document.getElementById('start-calling');
        const stopBtn = document.getElementById('stop-calling');
        const progressDiv = document.getElementById('call-progress');
        const statusIndicator = document.getElementById('system-status');
        
        if (this.isCallInProgress) {
            if (startBtn) startBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
            if (progressDiv) progressDiv.style.display = 'block';
            
            if (statusIndicator) {
                statusIndicator.innerHTML = `
                    <span class="status-dot calling"></span>
                    <span class="status-text">Calling in Progress</span>
                `;
            }
        } else {
            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
            if (progressDiv) progressDiv.style.display = 'none';
            
            if (statusIndicator) {
                statusIndicator.innerHTML = `
                    <span class="status-dot ready"></span>
                    <span class="status-text">System Ready</span>
                `;
            }
        }
    }
    
    startCallProgressPolling() {
        this.callProgressInterval = setInterval(async () => {
            try {
                const response = await fetch('/call-progress');
                const result = await response.json();
                
                if (result.status === 'success') {
                    this.updateCallProgress(result.progress);
                    
                    if (result.progress.completed) {
                        this.isCallInProgress = false;
                        this.stopCallProgressPolling();
                        this.updateCallControlUI();
                        this.loadCallLogs();
                        this.updateStats();
                    }
                }
            } catch (error) {
                console.error('Error polling call progress:', error);
            }
        }, 2000); // Poll every 2 seconds
    }
    
    stopCallProgressPolling() {
        if (this.callProgressInterval) {
            clearInterval(this.callProgressInterval);
            this.callProgressInterval = null;
        }
    }
    
    updateCallProgress(progress) {
        const currentCallElement = document.getElementById('current-call');
        const callCounterElement = document.getElementById('call-counter');
        const progressBarElement = document.getElementById('progress-bar');
        const progressPercentageElement = document.getElementById('progress-percentage');
        const estimatedTimeElement = document.getElementById('estimated-time');
        
        if (currentCallElement) {
            currentCallElement.textContent = progress.current_number || 'Preparing...';
        }
        
        if (callCounterElement) {
            callCounterElement.textContent = `${progress.current_index || 0} / ${progress.total || 0}`;
        }
        
        if (progressBarElement) {
            const percentage = progress.total > 0 ? (progress.current_index / progress.total) * 100 : 0;
            progressBarElement.style.width = `${percentage}%`;
            progressBarElement.setAttribute('aria-valuenow', percentage);
        }
        
        if (progressPercentageElement) {
            const percentage = progress.total > 0 ? Math.round((progress.current_index / progress.total) * 100) : 0;
            progressPercentageElement.textContent = `${percentage}%`;
        }
        
        if (estimatedTimeElement && progress.estimated_time) {
            estimatedTimeElement.textContent = `ETA: ${progress.estimated_time}`;
        }
    }
    
    // Statistics Functions
    startStatsPolling() {
        this.updateStats(); // Initial load
        this.statsUpdateInterval = setInterval(() => {
            this.updateStats();
        }, 10000); // Update every 10 seconds
    }
    
    async updateStats() {
        try {
            const response = await fetch('/call-stats');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.displayStats(result.stats);
            }
        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }
    
    displayStats(stats) {
        const totalElement = document.getElementById('total-calls');
        const successfulElement = document.getElementById('successful-calls');
        const failedElement = document.getElementById('failed-calls');
        const rateElement = document.getElementById('success-rate');
        
        if (totalElement) totalElement.textContent = stats.total || 0;
        if (successfulElement) successfulElement.textContent = stats.successful || 0;
        if (failedElement) failedElement.textContent = stats.failed || 0;
        if (rateElement) {
            const rate = stats.total > 0 ? Math.round((stats.successful / stats.total) * 100) : 0;
            rateElement.textContent = `${rate}%`;
        }
    }
    
    // Call Logs Functions
    async loadCallLogs() {
        try {
            const response = await fetch('/call-logs');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.displayCallLogs(result.call_logs || result.logs);
            } else {
                this.showStatus('Failed to load call logs', 'error');
            }
        } catch (error) {
            console.error('Error loading call logs:', error);
            this.showStatus('Error loading call logs', 'error');
        }
    }
    
    displayCallLogs(logs) {
        const container = document.getElementById('call-logs-table');
        if (!container) return;
        
        if (!logs || logs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📋</span>
                    <p>No call logs available</p>
                    <p class="empty-subtext">Start making calls to see logs here</p>
                </div>
            `;
            return;
        }
        
        const tableHTML = `
            <table class="logs-table">
                <thead>
                    <tr>
                        <th>Phone Number</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Timestamp</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
                    ${logs.map(log => `
                        <tr>
                            <td>${log.phone_number}</td>
                            <td><span class="status-badge ${log.status}">${log.status}</span></td>
                            <td>${log.duration ? log.duration + 's' : '-'}</td>
                            <td>${new Date(log.created_at).toLocaleString()}</td>
                            <td>${log.error_message || '-'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        container.innerHTML = tableHTML;
    }
    
    filterLogs() {
        const searchTerm = document.getElementById('log-search')?.value.toLowerCase() || '';
        const statusFilter = document.getElementById('status-filter')?.value || '';
        
        const rows = document.querySelectorAll('.logs-table tbody tr');
        
        rows.forEach(row => {
            const phoneNumber = row.cells[0].textContent.toLowerCase();
            const status = row.cells[1].textContent.toLowerCase();
            
            const matchesSearch = phoneNumber.includes(searchTerm);
            const matchesStatus = !statusFilter || status.includes(statusFilter);
            
            row.style.display = matchesSearch && matchesStatus ? '' : 'none';
        });
    }
    
    async clearLogs() {
        if (!confirm('Are you sure you want to clear all call logs? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch('/clear-logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.showStatus('Call logs cleared successfully', 'success');
                this.loadCallLogs();
                this.updateStats();
            } else {
                this.showStatus(result.message || 'Failed to clear logs', 'error');
            }
        } catch (error) {
            console.error('Error clearing logs:', error);
            this.showStatus('Error clearing logs. Please try again.', 'error');
        }
    }
    
    async exportLogs() {
        try {
            const response = await fetch('/export-logs');
            const blob = await response.blob();
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `call-logs-${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showStatus('Call logs exported successfully', 'success');
        } catch (error) {
            console.error('Error exporting logs:', error);
            this.showStatus('Error exporting logs. Please try again.', 'error');
        }
    }
    
    // Keyboard Shortcuts
    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + Enter to execute AI command
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const aiInput = document.getElementById('ai-command');
            if (document.activeElement === aiInput) {
                this.processCommand();
                e.preventDefault();
            }
        }
        
        // Ctrl/Cmd + S to start calling
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            this.startCalling();
            e.preventDefault();
        }
        
        // Ctrl/Cmd + X to stop calling
        if ((e.ctrlKey || e.metaKey) && e.key === 'x') {
            this.stopCalling();
            e.preventDefault();
        }
        
        // Ctrl/Cmd + R to refresh logs
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            this.loadCallLogs();
            e.preventDefault();
        }
    }
    
    // Initial Data Loading
    async loadInitialData() {
        await this.loadCurrentNumbers();
        await this.loadCallLogs();
        await this.updateStats();
    }
    
    // Cleanup
    destroy() {
        if (this.callProgressInterval) {
            clearInterval(this.callProgressInterval);
        }
        if (this.statsUpdateInterval) {
            clearInterval(this.statsUpdateInterval);
        }
    }
}

// Global functions for backward compatibility and HTML onclick handlers
let app;

function showStatus(message, isError = false) {
    if (app) {
        app.showStatus(message, isError ? 'error' : 'success');
    }
}

function uploadNumbers() {
    if (app) app.uploadNumbers();
}

function uploadFile() {
    if (app) app.processFile(document.getElementById('file-upload').files[0]);
}

function addSingleNumber() {
    if (app) app.addSingleNumber();
}

function processCommand() {
    if (app) app.processCommand();
}

function quickCommand(command) {
    if (app) app.quickCommand(command);
}

function setCommand(command) {
    if (app) app.setCommand(command);
}

function startCalling() {
    if (app) app.startCalling();
}

function stopCalling() {
    if (app) app.stopCalling();
}

function loadCallLogs() {
    if (app) app.loadCallLogs();
}

function clearLogs() {
    if (app) app.clearLogs();
}

function exportLogs() {
    if (app) app.exportLogs();
}

function filterLogs() {
    if (app) app.filterLogs();
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    app = new AutodialerApp();
    
    // Add helpful tooltips
    const tooltips = {
        'start-calling': 'Keyboard shortcut: Ctrl+S',
        'stop-calling': 'Keyboard shortcut: Ctrl+X',
        'ai-command': 'Press Ctrl+Enter to execute command',
        'log-search': 'Search by phone number or status'
    };
    
    Object.entries(tooltips).forEach(([id, tooltip]) => {
        const element = document.getElementById(id);
        if (element) {
            element.title = tooltip;
        }
    });
});

// Handle page unload
window.addEventListener('beforeunload', function() {
    if (app) {
        app.destroy();
    }
});