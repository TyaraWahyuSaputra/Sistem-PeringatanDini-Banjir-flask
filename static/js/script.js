// ==================== GLOBAL UTILITIES ====================

// Toast Notification System
class ToastSystem {
    constructor() {
        this.container = null;
        this.init();
    }
    
    init() {
        // Create toast container
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    }
    
    show(message, type = 'info', title = '', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-content">
                ${title ? `<div class="toast-title">${title}</div>` : ''}
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">&times;</button>
        `;
        
        this.container.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.hide(toast), duration);
        }
        
        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => this.hide(toast));
        
        return toast;
    }
    
    hide(toast) {
        toast.classList.remove('show');
        toast.classList.add('hide');
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 300);
    }
    
    success(message, title = 'Berhasil', duration = 3000) {
        return this.show(message, 'success', title, duration);
    }
    
    error(message, title = 'Error', duration = 5000) {
        return this.show(message, 'error', title, duration);
    }
    
    warning(message, title = 'Peringatan', duration = 4000) {
        return this.show(message, 'warning', title, duration);
    }
    
    info(message, title = 'Informasi', duration = 3000) {
        return this.show(message, 'info', title, duration);
    }
}

// Initialize toast system
const Toast = new ToastSystem();

// Global App Utilities
window.AppUtils = {
    // Show toast notification (replaces alert())
    notify: (message, type = 'info', title = '') => {
        Toast[type]?.(message, title) || Toast.info(message, title || 'Info');
    },
    
    // Form validation helper
    validateForm: (form) => {
        const elements = form.elements;
        let isValid = true;
        const errors = [];
        
        for (let element of elements) {
            if (element.hasAttribute('required') && !element.value.trim()) {
                const label = element.getAttribute('data-label') || 
                            element.previousElementSibling?.textContent || 
                            element.name;
                errors.push(`${label} harus diisi`);
                isValid = false;
                
                // Add error class
                element.classList.add('is-invalid');
                element.addEventListener('input', function() {
                    if (this.value.trim()) {
                        this.classList.remove('is-invalid');
                    }
                }, { once: true });
            }
            
            // Email validation
            if (element.type === 'email' && element.value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(element.value)) {
                    errors.push('Format email tidak valid');
                    isValid = false;
                    element.classList.add('is-invalid');
                }
            }
            
            // Phone validation
            if ((element.type === 'tel' || element.name.includes('phone')) && element.value) {
                const phoneRegex = /^(\+62|62|0)8[1-9][0-9]{6,9}$/;
                const cleanPhone = element.value.replace(/[-+\s]/g, '');
                if (!phoneRegex.test(cleanPhone)) {
                    errors.push('Format nomor telepon tidak valid');
                    isValid = false;
                    element.classList.add('is-invalid');
                }
            }
        }
        
        if (!isValid && errors.length > 0) {
            Toast.error(errors.join('<br>'), 'Validasi Gagal');
        }
        
        return isValid;
    },
    
    // Loading states
    showLoading: (element, text = 'Memuat...') => {
        const originalHTML = element.innerHTML;
        element.disabled = true;
        element.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2"></span>
            ${text}
        `;
        return originalHTML;
    },
    
    hideLoading: (element, originalHTML) => {
        element.disabled = false;
        element.innerHTML = originalHTML;
    },
    
    // Format date
    formatDate: (dateString, format = 'dd/mm/yyyy') => {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;
        
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const year = date.getFullYear();
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        
        switch(format) {
            case 'dd/mm/yyyy': return `${day}/${month}/${year}`;
            case 'dd-mm-yyyy': return `${day}-${month}-${year}`;
            case 'yyyy-mm-dd': return `${year}-${month}-${day}`;
            case 'dd/mm/yyyy HH:mm': return `${day}/${month}/${year} ${hours}:${minutes}`;
            case 'HH:mm': return `${hours}:${minutes}`;
            default: return date.toLocaleDateString();
        }
    },
    
    // Format file size
    formatFileSize: (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Debounce function
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Throttle function
    throttle: (func, limit) => {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // Copy to clipboard
    copyToClipboard: (text) => {
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text)
                .then(() => Toast.success('Teks berhasil disalin', 'Clipboard'))
                .catch(() => Toast.error('Gagal menyalin teks', 'Clipboard'));
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                document.execCommand('copy');
                Toast.success('Teks berhasil disalin', 'Clipboard');
            } catch (err) {
                Toast.error('Gagal menyalin teks', 'Clipboard');
            }
            
            document.body.removeChild(textArea);
        }
    }
};

// ==================== MAIN INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeMobileMenu();
    initializeFormValidation();
    initializeFileUploads();
    initializeTooltips();
    initializeDataTables();
    initializeCharts();
    initializeAnimations();
    
    // Show welcome message
    setTimeout(() => {
        if (window.location.pathname === '/') {
            Toast.info('Selamat datang di Sistem Peringatan Dini Banjir', 'Sistem Banjir');
        }
    }, 1000);
});

// ==================== MOBILE MENU ====================

function initializeMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navMenu = document.getElementById('navMenu');
    
    if (mobileMenuBtn && navMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            this.classList.toggle('active');
            this.innerHTML = navMenu.classList.contains('active') ? 
                '✕' : '☰';
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!navMenu.contains(event.target) && 
                !mobileMenuBtn.contains(event.target) && 
                navMenu.classList.contains('active')) {
                navMenu.classList.remove('active');
                mobileMenuBtn.classList.remove('active');
                mobileMenuBtn.innerHTML = '☰';
            }
        });
        
        // Close menu when clicking a link
        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
                mobileMenuBtn.classList.remove('active');
                mobileMenuBtn.innerHTML = '☰';
            });
        });
    }
}

// ==================== FORM VALIDATION ====================

function initializeFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!AppUtils.validateForm(this)) {
                e.preventDefault();
            } else {
                // Show loading state
                const submitBtn = this.querySelector('button[type="submit"]');
                if (submitBtn) {
                    AppUtils.showLoading(submitBtn, 'Mengirim...');
                }
            }
        });
        
        // Real-time validation
        form.querySelectorAll('[required]').forEach(input => {
            input.addEventListener('blur', function() {
                if (this.value.trim() === '') {
                    this.classList.add('is-invalid');
                } else {
                    this.classList.remove('is-invalid');
                }
            });
            
            input.addEventListener('input', function() {
                this.classList.remove('is-invalid');
            });
        });
    });
}

// ==================== FILE UPLOADS ====================

function initializeFileUploads() {
    const fileInputs = document.querySelectorAll('input[type="file"][data-preview]');
    
    fileInputs.forEach(input => {
        const previewId = input.getAttribute('data-preview');
        const previewElement = document.getElementById(previewId);
        
        if (previewElement) {
            input.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    // Validate file size (5MB max)
                    if (file.size > 5 * 1024 * 1024) {
                        Toast.error('Ukuran file maksimal 5MB', 'Upload Gagal');
                        this.value = '';
                        return;
                    }
                    
                    // Validate file type
                    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
                    if (!allowedTypes.includes(file.type)) {
                        Toast.error('Format file harus JPG, PNG, atau GIF', 'Upload Gagal');
                        this.value = '';
                        return;
                    }
                    
                    // Create preview
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        if (previewElement.tagName === 'IMG') {
                            previewElement.src = e.target.result;
                        } else {
                            previewElement.innerHTML = `
                                <img src="${e.target.result}" 
                                     alt="Preview" 
                                     style="max-width: 100%; border-radius: 8px;">
                            `;
                        }
                        previewElement.style.display = 'block';
                        
                        Toast.success('File berhasil diunggah', 'Upload Sukses');
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    });
}

// ==================== TOOLTIPS ====================

function initializeTooltips() {
    // Use native title attribute with custom styling
    const tooltipElements = document.querySelectorAll('[title]');
    
    tooltipElements.forEach(element => {
        element.setAttribute('data-tooltip', element.getAttribute('title'));
        element.removeAttribute('title');
    });
}

// ==================== DATA TABLES ====================

function initializeDataTables() {
    const tables = document.querySelectorAll('.table[data-sortable]');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th[data-sortable]');
        
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const columnIndex = Array.from(this.parentNode.children).indexOf(this);
                const rows = Array.from(table.querySelectorAll('tbody tr'));
                const isAscending = !this.classList.contains('asc');
                
                // Clear other sort indicators
                headers.forEach(h => {
                    h.classList.remove('asc', 'desc');
                });
                
                // Set current sort indicator
                this.classList.toggle('asc', isAscending);
                this.classList.toggle('desc', !isAscending);
                
                // Sort rows
                rows.sort((a, b) => {
                    const aValue = a.children[columnIndex].textContent.trim();
                    const bValue = b.children[columnIndex].textContent.trim();
                    
                    // Try to compare as numbers
                    const aNum = parseFloat(aValue);
                    const bNum = parseFloat(bValue);
                    
                    if (!isNaN(aNum) && !isNaN(bNum)) {
                        return isAscending ? aNum - bNum : bNum - aNum;
                    }
                    
                    // Otherwise compare as strings
                    return isAscending ? 
                        aValue.localeCompare(bValue) : 
                        bValue.localeCompare(aValue);
                });
                
                // Reappend sorted rows
                const tbody = table.querySelector('tbody');
                rows.forEach(row => tbody.appendChild(row));
                
                Toast.info(`Tabel diurutkan berdasarkan ${this.textContent}`, 'Sorting');
            });
        });
    });
}

// ==================== CHARTS ====================

function initializeCharts() {
    // Initialize Chart.js if available
    if (typeof Chart !== 'undefined') {
        const chartCanvases = document.querySelectorAll('canvas[data-chart]');
        
        chartCanvases.forEach(canvas => {
            const chartType = canvas.getAttribute('data-chart') || 'line';
            const data = JSON.parse(canvas.getAttribute('data-chart-data') || '{}');
            
            if (Object.keys(data).length > 0) {
                new Chart(canvas.getContext('2d'), {
                    type: chartType,
                    data: data,
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'top',
                            },
                            tooltip: {
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.1)'
                                }
                            },
                            x: {
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.1)'
                                }
                            }
                        }
                    }
                });
            }
        });
    }
}

// ==================== ANIMATIONS ====================

function initializeAnimations() {
    // Add fade-in animation to cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe all cards and metric cards
    document.querySelectorAll('.card, .metric-card').forEach(card => {
        observer.observe(card);
    });
    
    // Add hover animations
    document.querySelectorAll('.btn, .card').forEach(element => {
        element.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        element.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// ==================== API CALLS ====================

async function fetchAPI(endpoint, options = {}) {
    try {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };
        
        // Show loading
        Toast.info('Memuat data...', 'Loading');
        
        const response = await fetch(endpoint, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Hide loading
        setTimeout(() => Toast.hide(), 500);
        
        return data;
        
    } catch (error) {
        console.error('API Error:', error);
        Toast.error('Gagal mengambil data', 'Error');
        throw error;
    }
}

// ==================== EXPORT FUNCTIONS ====================

function exportToCSV(data, filename) {
    if (!data || data.length === 0) {
        Toast.warning('Tidak ada data untuk diekspor', 'Export');
        return;
    }
    
    // Convert data to CSV
    const headers = Object.keys(data[0]);
    const csvRows = [
        headers.join(','),
        ...data.map(row => 
            headers.map(header => 
                JSON.stringify(row[header] || '')
            ).join(',')
        )
    ];
    
    const csvString = csvRows.join('\n');
    const blob = new Blob(['\ufeff' + csvString], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    
    a.href = url;
    a.download = filename || `export_${new Date().toISOString().split('T')[0]}.csv`;
    a.style.display = 'none';
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    Toast.success('Data berhasil diekspor', 'Export');
}

// ==================== PAGE LOADER ====================

function showPageLoader(message = 'Memuat halaman...') {
    const loader = document.createElement('div');
    loader.className = 'page-loader';
    loader.innerHTML = `
        <div class="page-loader-content">
            <div class="page-loader-spinner"></div>
            <p>${message}</p>
        </div>
    `;
    
    document.body.appendChild(loader);
    
    return loader;
}

function hidePageLoader(loader) {
    if (loader) {
        loader.classList.add('hidden');
        setTimeout(() => {
            if (loader.parentElement) {
                loader.remove();
            }
        }, 300);
    }
}

// Auto-show page loader on navigation
document.addEventListener('click', function(e) {
    const link = e.target.closest('a');
    if (link && link.href && !link.href.includes('#') && link.target !== '_blank') {
        const loader = showPageLoader();
        setTimeout(() => hidePageLoader(loader), 3000); // Safety timeout
    }
});

// Hide loader when page is fully loaded
window.addEventListener('load', function() {
    const loader = document.querySelector('.page-loader');
    hidePageLoader(loader);
});

// ==================== ERROR HANDLING ====================

window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    Toast.error('Terjadi kesalahan pada aplikasi', 'System Error');
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    Toast.error('Terjadi kesalahan pada aplikasi', 'System Error');
});

// ==================== ADDITIONAL FUNCTIONS FOR BULANAN.HTML ====================

// Sync with Google Sheets
function syncWithGoogleSheets() {
    if (!confirm('Sync data dari Google Sheets ke database lokal?')) {
        return;
    }
    
    const btn = event.target;
    const originalText = btn.innerHTML;
    
    // Show loading
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Syncing...';
    btn.disabled = true;
    
    fetch('/api/sync-google-sheets', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Toast.success(data.message, 'Sync Success');
            // Refresh page after 2 seconds
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            Toast.error(data.message, 'Sync Failed');
        }
    })
    .catch(error => {
        Toast.error('Sync error: ' + error, 'Error');
    })
    .finally(() => {
        // Restore button
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// Refresh data
function refreshData() {
    window.location.reload();
}

// Show raw data in console
function showRawData() {
    // This would show raw data in console or modal
    console.log('Monthly Reports:', window.monthlyReports || 'Not available');
    console.log('Yearly Stats:', window.yearlyStats || 'Not available');
    
    Toast.info('Data logged to console. Press F12 to view.', 'Debug Info');
}

// Export monthly reports to CSV
function exportMonthlyToCSV() {
    if (!window.monthlyReports || window.monthlyReports.length === 0) {
        Toast.warning('Tidak ada data untuk diekspor', 'Export');
        return;
    }
    
    exportToCSV(window.monthlyReports, `laporan_bulanan_${new Date().toISOString().slice(0,7)}.csv`);
}

// Print table
function printTable() {
    window.print();
}

// View report detail
function viewReport(reportId) {
    Toast.info(`Viewing report #${reportId}. Feature coming soon!`, 'Info');
    // window.location.href = `/laporan/detail/${reportId}`;
}