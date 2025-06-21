// Legal RAG Agent Frontend
class LegalRAGApp {
    constructor() {
        this.apiBase = 'http://localhost:8000';
        this.selectedDocuments = new Set();
        this.currentSessionId = null;
        this.llmProvider = 'groq';
        this.searchAllMode = false;
        
        // Pagination and filtering
        this.currentPage = 1;
        this.pageSize = 25;
        this.totalDocuments = 0;
        this.filteredDocuments = [];
        this.allDocuments = [];
        this.searchQuery = '';
        this.statusFilter = '';
        this.typeFilter = '';
        this.sortBy = 'date_desc';
        
        // Selection state
        this.lastSelectedIndex = -1;
        
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
        this.documentCounter = document.getElementById('documentCounter');

        // Upload progress elements
        this.uploadProgress = document.getElementById('uploadProgress');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');

        // Search and filter elements
        this.documentSearch = document.getElementById('documentSearch');
        this.clearSearch = document.getElementById('clearSearch');
        this.statusFilterEl = document.getElementById('statusFilter');
        this.typeFilterEl = document.getElementById('typeFilter');
        this.sortByEl = document.getElementById('sortBy');

        // Selection elements
        this.selectAllBtn = document.getElementById('selectAllBtn');
        this.clearSelectionBtn = document.getElementById('clearSelectionBtn');
        this.bulkActions = document.getElementById('bulkActions');
        this.deleteSelected = document.getElementById('deleteSelected');

        // Pagination elements
        this.pagination = document.getElementById('pagination');
        this.prevPage = document.getElementById('prevPage');
        this.nextPage = document.getElementById('nextPage');
        this.pageInfo = document.getElementById('pageInfo');
        this.pageSizeEl = document.getElementById('pageSize');

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
        this.uploadBtn.addEventListener('click', () => this.uploadDocuments());

        // Search and filter
        this.documentSearch.addEventListener('input', (e) => this.handleSearch(e.target.value));
        this.clearSearch.addEventListener('click', () => this.clearSearchInput());
        this.statusFilterEl.addEventListener('change', (e) => this.handleFilterChange('status', e.target.value));
        this.typeFilterEl.addEventListener('change', (e) => this.handleFilterChange('type', e.target.value));
        this.sortByEl.addEventListener('change', (e) => this.handleSortChange(e.target.value));

        // Selection
        this.selectAllBtn.addEventListener('click', () => this.selectAllDocuments());
        this.clearSelectionBtn.addEventListener('click', () => this.clearSelection());
        this.deleteSelected.addEventListener('click', () => this.deleteSelectedDocuments());

        // Pagination
        this.prevPage.addEventListener('click', () => this.changePage(this.currentPage - 1));
        this.nextPage.addEventListener('click', () => this.changePage(this.currentPage + 1));
        this.pageSizeEl.addEventListener('change', (e) => this.changePageSize(parseInt(e.target.value)));

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
        const files = e.target.files;
        if (files.length > 0) {
            this.uploadBtn.disabled = false;
            const fileText = files.length === 1 
                ? `File selected: <strong>${files[0].name}</strong> (${this.formatFileSize(files[0].size)})`
                : `<strong>${files.length} files</strong> selected (${this.formatTotalFileSize(files)})`;
            this.uploadZone.querySelector('p').innerHTML = fileText;
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatTotalFileSize(files) {
        let totalSize = 0;
        for (let file of files) {
            totalSize += file.size;
        }
        return this.formatFileSize(totalSize);
    }

    async uploadDocuments() {
        const files = this.fileInput.files;
        if (!files || files.length === 0) return;

        // Show upload progress
        this.showUploadProgress();
        this.uploadBtn.disabled = true;

        let completed = 0;
        const total = files.length;

        try {
            const uploadPromises = [];
            for (let file of files) {
                const formData = new FormData();
                formData.append('file', file);

                const uploadPromise = this.uploadSingleDocument(formData, file.name)
                    .then(result => {
                        completed++;
                        this.updateUploadProgress(completed, total);
                        return result;
                    })
                    .catch(error => {
                        completed++;
                        this.updateUploadProgress(completed, total);
                        throw error;
                    });

                uploadPromises.push(uploadPromise);
            }

            const results = await Promise.allSettled(uploadPromises);
            const successful = results.filter(r => r.status === 'fulfilled').length;
            const failed = results.filter(r => r.status === 'rejected').length;

            if (successful > 0) {
                this.showToast(`Successfully uploaded ${successful} document(s)!`, 'success');
                this.resetUploadForm();
                this.loadDocuments();
            }

            if (failed > 0) {
                this.showToast(`Failed to upload ${failed} document(s)`, 'error');
            }
        } catch (error) {
            this.showToast(`Upload error: ${error.message}`, 'error');
        } finally {
            this.hideUploadProgress();
            this.uploadBtn.disabled = false;
        }
    }

    async uploadSingleDocument(formData, filename) {
        const response = await fetch(`${this.apiBase}/api/v1/documents/upload`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(`${filename}: ${result.detail || 'Upload error'}`);
        }

        return result;
    }

    resetUploadForm() {
        this.fileInput.value = '';
        this.uploadBtn.disabled = true;
        this.uploadZone.querySelector('p').innerHTML =
            'Drag documents here or <span class="upload-text">choose files</span>';
    }

    showUploadProgress() {
        this.uploadProgress.style.display = 'block';
        this.progressFill.style.width = '0%';
        this.progressText.textContent = 'Starting upload...';
    }

    updateUploadProgress(completed, total) {
        const percentage = Math.round((completed / total) * 100);
        this.progressFill.style.width = `${percentage}%`;
        this.progressText.textContent = `Uploading documents... ${completed}/${total} (${percentage}%)`;
    }

    hideUploadProgress() {
        this.uploadProgress.style.display = 'none';
    }

    // Search and Filter Functions
    handleSearch(query) {
        this.searchQuery = query.toLowerCase();
        this.clearSearch.style.display = query ? 'block' : 'none';
        this.currentPage = 1;
        this.applyFiltersAndPagination();
    }

    clearSearchInput() {
        this.documentSearch.value = '';
        this.searchQuery = '';
        this.clearSearch.style.display = 'none';
        this.currentPage = 1;
        this.applyFiltersAndPagination();
    }

    handleFilterChange(type, value) {
        if (type === 'status') {
            this.statusFilter = value;
        } else if (type === 'type') {
            this.typeFilter = value;
        }
        this.currentPage = 1;
        this.applyFiltersAndPagination();
    }

    handleSortChange(sortBy) {
        this.sortBy = sortBy;
        this.applyFiltersAndPagination();
    }

    applyFiltersAndPagination() {
        // Filter documents
        this.filteredDocuments = this.allDocuments.filter(doc => {
            // Search filter
            if (this.searchQuery && !doc.filename.toLowerCase().includes(this.searchQuery)) {
                return false;
            }

            // Status filter
            if (this.statusFilter && doc.processing_status !== this.statusFilter) {
                return false;
            }

            // Type filter
            if (this.typeFilter) {
                const extension = doc.filename.split('.').pop().toLowerCase();
                if (extension !== this.typeFilter) {
                    return false;
                }
            }

            return true;
        });

        // Sort documents
        this.filteredDocuments.sort((a, b) => {
            switch (this.sortBy) {
                case 'date_desc':
                    return new Date(b.uploaded_at) - new Date(a.uploaded_at);
                case 'date_asc':
                    return new Date(a.uploaded_at) - new Date(b.uploaded_at);
                case 'name_asc':
                    return a.filename.localeCompare(b.filename);
                case 'name_desc':
                    return b.filename.localeCompare(a.filename);
                case 'size_desc':
                    return (b.file_size || 0) - (a.file_size || 0);
                case 'size_asc':
                    return (a.file_size || 0) - (b.file_size || 0);
                default:
                    return 0;
            }
        });

        this.totalDocuments = this.filteredDocuments.length;
        this.renderDocuments();
        this.updatePagination();
    }

    // Pagination Functions
    changePage(page) {
        const maxPage = Math.ceil(this.totalDocuments / this.pageSize);
        if (page >= 1 && page <= maxPage) {
            this.currentPage = page;
            this.renderDocuments();
            this.updatePagination();
        }
    }

    changePageSize(newSize) {
        this.pageSize = newSize;
        this.currentPage = 1;
        this.renderDocuments();
        this.updatePagination();
    }

    updatePagination() {
        const maxPage = Math.ceil(this.totalDocuments / this.pageSize);
        
        this.prevPage.disabled = this.currentPage <= 1;
        this.nextPage.disabled = this.currentPage >= maxPage;
        
        this.pageInfo.textContent = `Page ${this.currentPage} of ${maxPage}`;
        
        this.pagination.style.display = maxPage > 1 ? 'flex' : 'none';
    }

    // Documents Management
    async loadDocuments() {
        try {
            // Load all documents (no pagination on API level for now)
            const response = await fetch(`${this.apiBase}/api/v1/documents/?limit=1000`);
            const data = await response.json();

            if (response.ok) {
                this.allDocuments = data.documents || [];
                this.applyFiltersAndPagination();
                this.updateDocumentCounter();

                // Check if there are documents still processing
                const hasProcessingDocs = this.allDocuments.some(doc =>
                    doc.processing_status === 'processing' || doc.processing_status === 'pending'
                );

                if (hasProcessingDocs) {
                    // Auto-refresh every 3 seconds if documents are still processing
                    setTimeout(() => this.loadDocuments(), 3000);
                }

                // Auto-enable chat if documents are available
                if (this.allDocuments.length > 0) {
                    setTimeout(() => {
                        if (this.selectedDocuments.size === 0) {
                            // Select first document if none selected
                            this.selectedDocuments.add(this.allDocuments[0].id);
                            this.updateSelectionDisplay();
                        }
                        this.enableChat();
                    }, 500);
                }
            } else {
                throw new Error(`API Error: ${response.status} - ${data.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.showToast(`Error loading documents: ${error.message}`, 'error');
        }
    }

    updateDocumentCounter() {
        const total = this.allDocuments.length;
        const text = total === 1 ? '1 document' : `${total} documents`;
        this.documentCounter.querySelector('span').textContent = text;
    }

    renderDocuments() {
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const documentsToShow = this.filteredDocuments.slice(startIndex, endIndex);

        if (documentsToShow.length === 0) {
            this.documentsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>${this.allDocuments.length === 0 ? 'No documents uploaded' : 'No documents match your filters'}</p>
                </div>
            `;
            return;
        }

        this.documentsList.innerHTML = documentsToShow.map((doc, index) => {
            const actualIndex = startIndex + index;
            const isSelected = this.selectedDocuments.has(doc.id);

            return `
                <div class="document-item ${isSelected ? 'selected' : ''}"
                     data-document-id="${doc.id}"
                     data-index="${actualIndex}">
                    <input type="checkbox" ${isSelected ? 'checked' : ''}
                           onclick="event.stopPropagation()">
                    <div class="document-content">
                        <div class="document-name">${doc.filename}</div>
                        <div class="document-meta">
                            <div>
                                <span class="document-status ${this.getStatusClass(doc.processing_status)}">
                                    ${this.getStatusText(doc.processing_status)}
                                </span>
                                ${doc.file_size ? `• ${this.formatFileSize(doc.file_size)}` : ''}
                            </div>
                            <div>
                                Uploaded: ${new Date(doc.uploaded_at).toLocaleDateString()}
                                ${doc.chunk_count ? `• ${doc.chunk_count} chunks` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="document-actions">
                        <button class="btn-delete" onclick="app.deleteDocument('${doc.id}', '${doc.filename}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Add click event listeners to document items
        this.documentsList.querySelectorAll('.document-item').forEach(item => {
            item.addEventListener('click', (e) => this.handleDocumentClick(e));
            
            const checkbox = item.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', (e) => this.handleCheckboxChange(e));
        });
    }

    handleDocumentClick(e) {
        const item = e.currentTarget;
        const documentId = item.dataset.documentId;
        const index = parseInt(item.dataset.index);
        const isCtrlPressed = e.ctrlKey || e.metaKey;
        const isShiftPressed = e.shiftKey;

        if (isShiftPressed && this.lastSelectedIndex !== -1) {
            // Range selection
            const start = Math.min(this.lastSelectedIndex, index);
            const end = Math.max(this.lastSelectedIndex, index);
            
            for (let i = start; i <= end; i++) {
                if (i < this.filteredDocuments.length) {
                    this.selectedDocuments.add(this.filteredDocuments[i].id);
                }
            }
        } else if (isCtrlPressed) {
            // Toggle selection
            if (this.selectedDocuments.has(documentId)) {
                this.selectedDocuments.delete(documentId);
            } else {
                this.selectedDocuments.add(documentId);
            }
        } else {
            // Single selection
            this.selectedDocuments.clear();
            this.selectedDocuments.add(documentId);
        }

        this.lastSelectedIndex = index;
        this.updateSelectionDisplay();
    }

    handleCheckboxChange(e) {
        const item = e.target.closest('.document-item');
        const documentId = item.dataset.documentId;
        
        if (e.target.checked) {
            this.selectedDocuments.add(documentId);
        } else {
            this.selectedDocuments.delete(documentId);
        }
        
        this.updateSelectionDisplay();
    }

    updateSelectionDisplay() {
        // Update visual selection
        this.documentsList.querySelectorAll('.document-item').forEach(item => {
            const documentId = item.dataset.documentId;
            const checkbox = item.querySelector('input[type="checkbox"]');
            const isSelected = this.selectedDocuments.has(documentId);

            item.classList.toggle('selected', isSelected);
            checkbox.checked = isSelected;
        });

        // Update selection controls
        const selectedCount = this.selectedDocuments.size;
        this.bulkActions.style.display = selectedCount > 0 ? 'flex' : 'none';
        this.clearSelectionBtn.style.display = selectedCount > 0 ? 'inline-flex' : 'none';

        // Update chat placeholder
        this.enableChat();
    }

    selectAllDocuments() {
        const documentsOnPage = this.filteredDocuments.slice(
            (this.currentPage - 1) * this.pageSize,
            this.currentPage * this.pageSize
        );
        
        documentsOnPage.forEach(doc => {
            this.selectedDocuments.add(doc.id);
        });
        
        this.updateSelectionDisplay();
    }

    clearSelection() {
        this.selectedDocuments.clear();
        this.updateSelectionDisplay();
    }

    async deleteSelectedDocuments() {
        if (this.selectedDocuments.size === 0) return;

        const confirmed = confirm(`Are you sure you want to delete ${this.selectedDocuments.size} document(s)?`);
        if (!confirmed) return;

        this.showLoading('Deleting documents...');

        try {
            const deletePromises = Array.from(this.selectedDocuments).map(docId => 
                fetch(`${this.apiBase}/api/v1/documents/${docId}`, { method: 'DELETE' })
            );

            await Promise.all(deletePromises);
            
            this.showToast(`Deleted ${this.selectedDocuments.size} document(s)`, 'success');
            this.selectedDocuments.clear();
            this.loadDocuments();
        } catch (error) {
            this.showToast('Error deleting documents', 'error');
        } finally {
            this.hideLoading();
        }
    }





    getStatusClass(status) {
        switch (status) {
            case 'completed':
            case 'ready':
                return 'status-completed';
            case 'processing':
                return 'status-processing';
            case 'pending':
                return 'status-pending';
            case 'failed':
                return 'status-failed';
            default:
                return 'status-pending';
        }
    }

    getStatusText(status) {
        switch (status) {
            case 'completed':
                return 'Ready';
            case 'processing':
                return 'Processing...';
            case 'pending':
                return 'Pending';
            case 'failed':
                return 'Failed';
            default:
                return 'Unknown';
        }
    }

    async deleteDocument(documentId, filename) {
        const confirmed = confirm(`Are you sure you want to delete "${filename}"?`);
        if (!confirmed) return;

        this.showLoading('Deleting document...');

        try {
            const response = await fetch(`${this.apiBase}/api/v1/documents/${documentId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showToast('Document deleted successfully!', 'success');
                this.selectedDocuments.delete(documentId);
                this.loadDocuments();
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Delete error');
            }
        } catch (error) {
            this.showToast(`Delete error: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    enableChat() {
        const hasDocuments = this.allDocuments.length > 0;
        const hasSelected = this.selectedDocuments.size > 0 || this.searchAllMode;
        
        this.messageInput.disabled = !hasDocuments;
        this.sendBtn.disabled = !hasDocuments;
        
        if (hasDocuments) {
            const placeholder = this.selectedDocuments.size > 0
                ? `Ask a question about ${this.selectedDocuments.size} selected document(s)...`
                : 'Ask a question about the documents...';
            this.messageInput.placeholder = placeholder;
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Determine which documents to search
        let documentIds = [];
        if (this.selectedDocuments.size > 0) {
            documentIds = Array.from(this.selectedDocuments);
        } else {
            // If no documents selected, use all completed documents
            documentIds = this.allDocuments.filter(doc => doc.processing_status === 'completed').map(doc => doc.id);
        }

        if (documentIds.length === 0) {
            this.showToast('No documents available for search', 'error');
            return;
        }

        // Add user message
        this.addMessage(message, 'user');
        this.messageInput.value = '';

        // Add loading message
        const loadingId = this.addLoadingMessage();

        try {
            // Always use iterative RAG
            const endpoint = '/api/v1/chat/iterative';
            
            const requestBody = {
                message: message,
                document_ids: documentIds,
                llm_provider: this.llmProvider,
                session_id: this.currentSessionId
            };

            const response = await fetch(`${this.apiBase}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (response.ok) {
                this.currentSessionId = data.session_id;
                
                // Remove loading message
                this.removeLoadingMessage(loadingId);
                
                // Add bot response
                this.addMessage(data.response, 'bot', data.sources || [], data.metadata);
                
                // Show success toast with stats
                if (data.metadata) {
                    const stats = data.metadata.search_stats || {};
                    this.showToast(`Response generated using ${stats.total_chunks || 'unknown'} chunks from ${documentIds.length} document(s)`, 'info');
                }
            } else {
                throw new Error(data.detail || 'Chat error');
            }
        } catch (error) {
            this.removeLoadingMessage(loadingId);
            this.addMessage(`Error: ${error.message}`, 'bot', [], null, true);
            this.showToast(`Chat error: ${error.message}`, 'error');
        }
    }

    addMessage(content, type, sources = [], metadata = null, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const timestamp = new Date().toLocaleTimeString();
        const avatarIcon = type === 'user' ? 'fas fa-user' : 'fas fa-robot';
        
        let sourcesHtml = '';
        if (sources && sources.length > 0) {
            sourcesHtml = `
                <div class="message-sources">
                    <h4><i class="fas fa-link"></i> Sources (${sources.length})</h4>
                    ${sources.map(source => this.formatSource(source)).join('')}
                </div>
            `;
        }

        // Format metadata if available
        let metadataHtml = '';
        if (metadata && metadata.search_stats) {
            const stats = metadata.search_stats;
            metadataHtml = `
                <div class="search-metadata">
                    <small>
                        <i class="fas fa-chart-bar"></i>
                        Search: ${stats.total_chunks || 0} chunks from ${stats.documents_searched || 0} documents
                        ${stats.iterations_used ? `• ${stats.iterations_used} iterations` : ''}
                        ${stats.search_time ? `• ${(stats.search_time * 1000).toFixed(0)}ms` : ''}
                    </small>
                </div>
            `;
        }

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="${avatarIcon}"></i>
            </div>
            <div class="message-content">
                <div class="markdown-content">${type === 'user' ? this.escapeHtml(content) : marked.parse(content)}</div>
                ${sourcesHtml}
                ${metadataHtml}
                <div class="message-time">${timestamp}</div>
            </div>
        `;

        if (isError) {
            messageDiv.classList.add('error-message');
        }

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        // Highlight code blocks
        messageDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    formatSource(source) {
        // Handle both old and new source formats
        const doc = source.document || {};
        const chunk = source.chunk || {};

        // Get document name from various possible fields
        const documentName = source.document_name ||
                            doc.filename ||
                            doc.name ||
                            doc.title ||
                            'Unknown Document';

        const relevanceScore = Math.round((source.similarity_score || 0) * 100);

        // Get chunk content from various possible fields
        const chunkContent = source.chunk_preview ||
                           chunk.content ||
                           chunk.text ||
                           '';

        const chunkType = source.chunk_type || chunk.chunk_type || 'content';
        const pageNumber = source.page_number || chunk.page_number;
        const sectionTitle = source.section_title || chunk.section_title;

        return `
            <div class="source-item">
                <div class="source-header">
                    <div class="source-doc">
                        <i class="fas fa-file-text"></i>
                        <span>${documentName}</span>
                    </div>
                    <div class="source-relevance">${relevanceScore}% match</div>
                </div>
                <div class="source-meta">
                    <span class="source-type">${chunkType}</span>
                    ${pageNumber ? `Page ${pageNumber}` : ''}
                    ${sectionTitle ? `• ${sectionTitle}` : ''}
                </div>
                ${chunkContent ? `<div class="source-preview">${this.truncateText(chunkContent, 200)}</div>` : ''}
            </div>
        `;
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return this.escapeHtml(text);
        return this.escapeHtml(text.substring(0, maxLength)) + '...';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    addLoadingMessage() {
        const loadingId = 'loading-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message loading-message';
        messageDiv.id = loadingId;
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <div class="message-time">Thinking...</div>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        return loadingId;
    }

    removeLoadingMessage(loadingId) {
        const loadingMessage = document.getElementById(loadingId);
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

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
        toast.textContent = message;

        this.toastContainer.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);

        // Remove on click
        toast.addEventListener('click', () => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        });
    }
}

// Initialize the app
const app = new LegalRAGApp();

// Demo mode function for testing
function enableDemoMode() {
    console.log('Demo mode enabled');
    app.showToast('Demo mode enabled - using mock data', 'info');
}