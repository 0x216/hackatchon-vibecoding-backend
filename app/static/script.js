// Legal RAG Agent Frontend
class LegalRAGApp {
    constructor() {
        this.apiBase = window.location.origin;
        this.selectedDocument = null;
        this.currentSessionId = null;
        this.llmProvider = 'groq';
        
        this.initializeElements();
        this.attachEventListeners();
        this.loadDocuments();
        this.checkAPIStatus();
    }

    initializeElements() {
        // Document elements
        this.uploadZone = document.getElementById('uploadZone');
        this.fileInput = document.getElementById('fileInput');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.documentsList = document.getElementById('documentsList');

        // Chat elements
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.llmSelector = document.getElementById('llmProvider');

        // UI elements
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');
        this.status = document.getElementById('status');
        this.toastContainer = document.getElementById('toastContainer');
    }

    attachEventListeners() {
        // File upload
        this.uploadZone.addEventListener('click', () => this.fileInput.click());
        this.uploadZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadZone.addEventListener('drop', (e) => this.handleDrop(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.uploadBtn.addEventListener('click', () => this.uploadDocument());

        // Chat
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // LLM provider selection
        this.llmSelector.addEventListener('change', (e) => {
            this.llmProvider = e.target.value;
            this.showToast(`Switched to ${e.target.options[e.target.selectedIndex].text}`, 'info');
        });

        // Quick questions
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const question = e.currentTarget.dataset.question;
                this.messageInput.value = question;
                this.sendMessage();
            });
        });
    }

    // API Status Check
    async checkAPIStatus() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            if (response.ok) {
                this.updateStatus('Ready to work', 'online');
            } else {
                this.updateStatus('Server issues', 'offline');
            }
        } catch (error) {
            this.updateStatus('Server unavailable', 'offline');
        }
    }

    updateStatus(message, type) {
        const statusElement = this.status.querySelector('span');
        const dotElement = this.status.querySelector('.status-dot');
        
        statusElement.textContent = message;
        
        if (type === 'online') {
            dotElement.style.color = '#48bb78';
        } else {
            dotElement.style.color = '#f56565';
        }
    }

    // File Upload Handlers
    handleDragOver(e) {
        e.preventDefault();
        this.uploadZone.classList.add('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.fileInput.files = files;
            this.handleFileSelect({ target: { files } });
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.uploadBtn.disabled = false;
            this.uploadZone.querySelector('p').innerHTML = 
                `File selected: <strong>${file.name}</strong> (${this.formatFileSize(file.size)})`;
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async uploadDocument() {
        const file = this.fileInput.files[0];
        if (!file) return;

        this.showLoading('Uploading document...');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${this.apiBase}/api/v1/documents/upload`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast('Document uploaded successfully!', 'success');
                this.resetUploadForm();
                this.loadDocuments();
            } else {
                throw new Error(result.detail || 'Upload error');
            }
        } catch (error) {
            this.showToast(`Upload error: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    resetUploadForm() {
        this.fileInput.value = '';
        this.uploadBtn.disabled = true;
        this.uploadZone.querySelector('p').innerHTML = 
            'Drag document here or <span class="upload-text">choose file</span>';
    }

    // Documents Management
    async loadDocuments() {
        try {
            const response = await fetch(`${this.apiBase}/api/v1/documents/`);
            const data = await response.json();

            if (response.ok) {
                this.renderDocuments(data.documents);
            } else {
                throw new Error('Error loading documents');
            }
        } catch (error) {
            console.error('Error loading documents:', error);
        }
    }

    renderDocuments(documents) {
        const container = this.documentsList;
        
        if (documents.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>No documents uploaded</p>
                </div>
            `;
            return;
        }

        container.innerHTML = documents.map(doc => `
            <div class="document-item" data-id="${doc.id}" onclick="app.selectDocument('${doc.id}', '${doc.filename}')">
                <div class="document-name">${doc.filename}</div>
                <div class="document-meta">
                    ${new Date(doc.upload_date).toLocaleDateString('ru-RU')} • ${this.formatFileSize(doc.file_size)}
                    <span class="document-status status-${doc.processing_status}">
                        ${this.getStatusText(doc.processing_status)}
                    </span>
                </div>
            </div>
        `).join('');

        // Enable chat if documents are available
        this.enableChat();
    }

    getStatusText(status) {
        const statusMap = {
            'processed': 'Processed',
            'processing': 'Processing',
            'pending': 'Pending'
        };
        return statusMap[status] || status;
    }

    selectDocument(documentId, filename) {
        // Remove previous selection
        document.querySelectorAll('.document-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Add selection to current item
        document.querySelector(`[data-id="${documentId}"]`).classList.add('selected');

        this.selectedDocument = { id: documentId, filename };
        this.showToast(`Selected document: ${filename}`, 'info');
        
        // Reset chat session for new document
        this.currentSessionId = null;
    }

    enableChat() {
        this.messageInput.disabled = false;
        this.sendBtn.disabled = false;
        this.messageInput.placeholder = "Ask a question about the uploaded document...";
        
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.disabled = false;
        });
    }

    // Chat Functionality
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        if (!this.selectedDocument) {
            this.showToast('Please select a document first', 'error');
            return;
        }

        // Add user message to chat
        this.addMessage(message, 'user');
        this.messageInput.value = '';

        // Show loading
        const loadingId = this.addLoadingMessage();
        
        try {
            const response = await fetch(`${this.apiBase}/api/v1/chat/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.currentSessionId,
                    llm_provider: this.llmProvider
                })
            });

            const result = await response.json();

            // Remove loading message
            this.removeLoadingMessage(loadingId);

            if (response.ok) {
                this.currentSessionId = result.session_id;
                this.addMessage(result.message, 'bot', result.sources, result);
            } else {
                throw new Error(result.detail || 'Request error');
            }
        } catch (error) {
            this.removeLoadingMessage(loadingId);
            this.addMessage(`Sorry, an error occurred: ${error.message}`, 'bot', [], null, true);
            this.showToast('Error processing request', 'error');
        }
    }

    addMessage(content, type, sources = [], metadata = null, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const time = new Date().toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        let sourcesHtml = '';
        if (sources && sources.length > 0) {
            sourcesHtml = `
                <div class="message-sources">
                    <h4><i class="fas fa-link"></i> Sources:</h4>
                    ${sources.map(source => `<div class="source-item">${source.title || source.text}</div>`).join('')}
                </div>
            `;
        }

        let metadataHtml = '';
        if (metadata && metadata.model_used) {
            metadataHtml = `
                <div class="message-time">
                    ${time} • ${metadata.model_used}
                    ${metadata.usage ? ` • ${metadata.usage.total_tokens} tokens` : ''}
                </div>
            `;
        } else {
            metadataHtml = `<div class="message-time">${time}</div>`;
        }

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-${type === 'user' ? 'user' : 'robot'}"></i>
            </div>
            <div class="message-content ${isError ? 'error' : ''}">
                <p>${content}</p>
                ${sourcesHtml}
                ${metadataHtml}
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addLoadingMessage() {
        const loadingId = Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.id = `loading-${loadingId}`;
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="spinner" style="width: 20px; height: 20px; margin: 0;"></div>
                <p style="margin-left: 30px; margin-top: -20px;">Processing request...</p>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        return loadingId;
    }

    removeLoadingMessage(loadingId) {
        const loadingElement = document.getElementById(`loading-${loadingId}`);
        if (loadingElement) {
            loadingElement.remove();
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    // UI Helpers
    showLoading(text = 'Loading...') {
        this.loadingText.textContent = text;
        this.loadingOverlay.classList.add('show');
    }

    hideLoading() {
        this.loadingOverlay.classList.remove('show');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'info': 'info-circle'
        }[type] || 'info-circle';

        toast.innerHTML = `
            <i class="fas fa-${icon}"></i>
            <span>${message}</span>
        `;

        this.toastContainer.appendChild(toast);

        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideInRight 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new LegalRAGApp();
});

// Demo mode for testing without documents
function enableDemoMode() {
    const app = window.app;
    app.selectedDocument = { id: 'demo', filename: 'Demo document' };
    app.enableChat();
    app.showToast('Demo mode activated!', 'info');
} 