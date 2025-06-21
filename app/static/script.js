// Legal RAG Agent Frontend
class LegalRAGApp {
    constructor() {
        this.apiBase = 'http://localhost:8000';
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
                
                // Check if there are documents still processing
                const hasProcessingDocs = data.documents.some(doc => 
                    doc.processing_status === 'processing' || doc.processing_status === 'pending'
                );
                
                if (hasProcessingDocs) {
                    // Auto-refresh every 3 seconds if documents are still processing
                    setTimeout(() => this.loadDocuments(), 3000);
                }
                
                // Auto-enable chat if documents are available
                if (data.documents && data.documents.length > 0) {
                    setTimeout(() => {
                        if (!this.selectedDocument) {
                            this.selectDocument(data.documents[0].id, data.documents[0].filename);
                        }
                        this.enableChat();
                    }, 500);
                }
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
            <div class="document-item" data-id="${doc.id}">
                <div class="document-content">
                    <div class="document-name">${doc.filename}</div>
                    <div class="document-meta">
                        ${new Date(doc.upload_date).toLocaleDateString('ru-RU')} • ${this.formatFileSize(doc.file_size)}
                        <span class="document-status status-${doc.processing_status}">
                            ${this.getStatusText(doc.processing_status)}
                        </span>
                    </div>
                </div>
                <div class="document-actions">
                    <button class="btn-delete" onclick="app.deleteDocument('${doc.id}', '${doc.filename}')" title="Delete document">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');

        // Add click event listeners to document items
        document.querySelectorAll('.document-item').forEach(item => {
            item.addEventListener('click', (event) => {
                const docId = item.dataset.id;
                const filename = item.querySelector('.document-name').textContent;
                this.selectDocument(docId, filename, event);
            });
        });

        // Enable chat if documents are available
        this.enableChat();
    }

    getStatusText(status) {
        const statusMap = {
            'completed': 'Completed ✅',
            'processed': 'Processed ✅',
            'processing': 'Processing ⏳',
            'pending': 'Pending ⏸️',
            'failed': 'Failed ❌'
        };
        return statusMap[status] || status;
    }

    selectDocument(documentId, filename, event) {
        const documentItem = document.querySelector(`[data-id="${documentId}"]`);
        
        // Initialize selectedDocuments array if not exists
        if (!this.selectedDocuments) {
            this.selectedDocuments = [];
        }

        // Check if Ctrl/Cmd key is pressed for multiple selection
        if (event && (event.ctrlKey || event.metaKey)) {
            // Toggle selection
            if (documentItem.classList.contains('selected')) {
                documentItem.classList.remove('selected');
                this.selectedDocuments = this.selectedDocuments.filter(doc => doc.id !== documentId);
                this.showToast(`Deselected document: ${filename}`, 'info');
            } else {
                documentItem.classList.add('selected');
                this.selectedDocuments.push({ id: documentId, filename });
                this.showToast(`Added document: ${filename}`, 'info');
            }
        } else {
            // Single selection (clear all others)
            document.querySelectorAll('.document-item').forEach(item => {
                item.classList.remove('selected');
            });
            documentItem.classList.add('selected');
            this.selectedDocuments = [{ id: documentId, filename }];
            this.showToast(`Selected document: ${filename}`, 'info');
        }

        // Update selected document for backward compatibility
        this.selectedDocument = this.selectedDocuments.length > 0 ? this.selectedDocuments[0] : null;
        
        // Reset chat session when selection changes
        this.currentSessionId = null;

        // Update UI to show selection count
        this.updateSelectionDisplay();
    }

    updateSelectionDisplay() {
        const count = this.selectedDocuments ? this.selectedDocuments.length : 0;
        const selectionInfo = document.querySelector('.selection-info');
        if (selectionInfo) {
            if (count > 1) {
                selectionInfo.textContent = `${count} documents selected`;
                selectionInfo.style.display = 'block';
            } else {
                selectionInfo.style.display = 'none';
            }
        }
    }

    async deleteDocument(documentId, filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
            return;
        }

        this.showLoading('Deleting document...');

        try {
            const response = await fetch(`${this.apiBase}/api/v1/documents/${documentId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showToast(`Document "${filename}" deleted successfully`, 'success');
                
                // Remove from selected documents if it was selected
                if (this.selectedDocuments) {
                    this.selectedDocuments = this.selectedDocuments.filter(doc => doc.id !== documentId);
                }
                
                // Update selected document if it was the deleted one
                if (this.selectedDocument && this.selectedDocument.id === documentId) {
                    this.selectedDocument = null;
                }
                
                // Reload documents list
                await this.loadDocuments();
                
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to delete document');
            }
        } catch (error) {
            this.showToast(`Failed to delete document: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
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
            // Auto-select first document if available
            const firstDoc = document.querySelector('.document-item');
            if (firstDoc) {
                const docId = firstDoc.dataset.id;
                const filename = firstDoc.querySelector('.document-name').textContent;
                this.selectDocument(docId, filename);
                this.enableChat();
            } else {
                this.showToast('Please select a document first', 'error');
                return;
            }
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
                    llm_provider: this.llmProvider,
                    document_ids: this.selectedDocuments ? this.selectedDocuments.map(doc => doc.id) : []
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
                    ${sources.map(source => `
                        <div class="source-item">
                            <div class="source-doc">${source.document_name || 'Unknown Document'}</div>
                            <div class="source-type">${source.chunk_type || 'general'} • Relevance: ${(source.similarity_score * 100).toFixed(1)}%</div>
                            <div class="source-preview">${source.chunk_preview || 'No preview available'}</div>
                        </div>
                    `).join('')}
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