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
                element.classList.add('error');
            } else {
                element.classList.remove('error');
            }
        }
        
        if (!isValid) {
            Toast.error(errors.join('<br>'), 'Validasi Gagal', 5000);
        }
        
        return isValid;
    },
    
    // Debounce function
    debounce: (func, wait = 300) => {
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
    
    // Format currency
    formatCurrency: (amount) => {
        return new Intl.NumberFormat('id-ID', {
            style: 'currency',
            currency: 'IDR',
            minimumFractionDigits: 0
        }).format(amount);
    },
    
    // Format date
    formatDate: (date, options = {}) => {
        const defaultOptions = {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };
        return new Intl.DateTimeFormat('id-ID', { ...defaultOptions, ...options }).format(new Date(date));
    },
    
    // Copy to clipboard
    copyToClipboard: async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            Toast.success('Berhasil disalin ke clipboard', 'Clipboard');
            return true;
        } catch (err) {
            Toast.error('Gagal menyalin ke clipboard', 'Error');
            return false;
        }
    },
    
    // Confirm dialog (modern)
    confirm: (message, title = 'Konfirmasi') => {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'confirm-modal';
            modal.innerHTML = `
                <div class="confirm-overlay"></div>
                <div class="confirm-dialog">
                    <h3>${title}</h3>
                    <p>${message}</p>
                    <div class="confirm-buttons">
                        <button class="btn btn-secondary confirm-cancel">Batal</button>
                        <button class="btn btn-primary confirm-ok">OK</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            const cleanup = () => {
                modal.remove();
            };
            
            modal.querySelector('.confirm-ok').addEventListener('click', () => {
                cleanup();
                resolve(true);
            });
            
            modal.querySelector('.confirm-cancel').addEventListener('click', () => {
                cleanup();
                resolve(false);
            });
            
            modal.querySelector('.confirm-overlay').addEventListener('click', () => {
                cleanup();
                resolve(false);
            });
        });
    },
    
    // Loading indicator
    showLoading: (message = 'Memuat...') => {
        let loader = document.querySelector('.app-loader');
        if (!loader) {
            loader = document.createElement('div');
            loader.className = 'app-loader';
            loader.innerHTML = `
                <div class="loader-content">
                    <div class="spinner"></div>
                    <p class="loader-message">${message}</p>
                </div>
            `;
            document.body.appendChild(loader);
        } else {
            loader.querySelector('.loader-message').textContent = message;
            loader.style.display = 'flex';
        }
    },
    
    hideLoading: () => {
        const loader = document.querySelector('.app-loader');
        if (loader) {
            loader.style.display = 'none';
        }
    }
};

// ==================== MAIN INITIALIZATION - FIXED ====================

// Track initialization status
let mobileMenuInitialized = false;

// Helper function to ensure mobile menu button is visible
function ensureMobileMenuVisible() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navMenu = document.getElementById('navMenu');
    
    if (mobileMenuBtn && navMenu) {
        // PENTING: Gunakan max-width 992px untuk konsisten dengan CSS @media query
        if (window.innerWidth <= 992) {
            mobileMenuBtn.style.display = 'block';
            mobileMenuBtn.style.visibility = 'visible';
            mobileMenuBtn.style.opacity = '1';
            console.log('✅ Mobile menu button forced visible (width: ' + window.innerWidth + 'px)');
        } else {
            mobileMenuBtn.style.display = 'none';
            console.log('🖥️ Desktop mode (width: ' + window.innerWidth + 'px)');
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing application...');
    
    // Initialize mobile menu FIRST (highest priority)
    initializeMobileMenu();
    ensureMobileMenuVisible();
    
    // Initialize other components
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
    
    console.log('✅ Application initialized');
});

// Additional check after page fully loads
window.addEventListener('load', function() {
    console.log('🔄 Page fully loaded, checking mobile menu...');
    ensureMobileMenuVisible();
    
    if (!mobileMenuInitialized) {
        console.log('⚠️ Mobile menu not initialized, retrying...');
        initializeMobileMenu();
    }
});

// Handle resize
let globalResizeTimeout;
window.addEventListener('resize', function() {
    clearTimeout(globalResizeTimeout);
    globalResizeTimeout = setTimeout(function() {
        ensureMobileMenuVisible();
    }, 100);
});

// ==================== MOBILE MENU - IMPROVED & FIXED ====================

// ==================== MOBILE MENU - IMPROVED & FIXED ====================

function initializeMobileMenu() {
    // Prevent multiple initialization
    if (mobileMenuInitialized) {
        console.log('⚠️ Mobile menu already initialized, skipping...');
        return;
    }
    
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navMenu = document.getElementById('navMenu');
    
    if (!mobileMenuBtn) {
        console.error('❌ Mobile menu button not found!');
        return;
    }
    
    if (!navMenu) {
        console.error('❌ Nav menu not found!');
        return;
    }
    
    console.log('✅ Mobile menu elements found');
    
    // Force display
    ensureMobileMenuVisible();
    
    // Create overlay element
    let navOverlay = document.querySelector('.nav-overlay');
    if (!navOverlay) {
        navOverlay = document.createElement('div');
        navOverlay.className = 'nav-overlay';
        navOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            opacity: 0;
            visibility: hidden;
            z-index: 998;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        `;
        document.body.appendChild(navOverlay);
    }
    
    function toggleMobileMenu() {
        const isActive = navMenu.classList.toggle('active');
        mobileMenuBtn.classList.toggle('active');
        
        if (isActive) {
            navOverlay.style.visibility = 'visible';
            navOverlay.style.opacity = '1';
            document.body.classList.add('menu-open');
        } else {
            navOverlay.style.opacity = '0';
            setTimeout(() => navOverlay.style.visibility = 'hidden', 300);
            document.body.classList.remove('menu-open');
        }
        
        mobileMenuBtn.innerHTML = isActive ? '✕' : '☰';
        
        if (isActive) {
            const menuItems = navMenu.querySelectorAll('li');
            menuItems.forEach((item, index) => {
                item.style.animation = `slideInFromTop 0.3s ease ${index * 0.05}s both`;
            });
        }
        
        console.log(`📱 Mobile menu ${isActive ? 'opened' : 'closed'}`);
    }
    
    function closeMobileMenu() {
        navMenu.classList.remove('active');
        mobileMenuBtn.classList.remove('active');
        navOverlay.style.opacity = '0';
        setTimeout(() => navOverlay.style.visibility = 'hidden', 300);
        document.body.classList.remove('menu-open');
        mobileMenuBtn.innerHTML = '☰';
    }
    
    // BUG FIX: Hapus cloning yang menyebabkan event listener hilang
    // Gunakan removeEventListener untuk menghindari duplicate listeners
    const clickHandler = function(e) {
        e.preventDefault();
        e.stopPropagation();
        toggleMobileMenu();
    };
    
    // Remove old listener if exists (safe way without cloning)
    mobileMenuBtn.removeEventListener('click', clickHandler);
    mobileMenuBtn.addEventListener('click', clickHandler);
    
    // Overlay click to close
    navOverlay.addEventListener('click', closeMobileMenu);
    
    // Click outside to close
    document.addEventListener('click', function(event) {
        if (!navMenu.contains(event.target) && 
            !mobileMenuBtn.contains(event.target) && 
            navMenu.classList.contains('active')) {
            closeMobileMenu();
        }
    });
    
    // Close menu when clicking menu items
    navMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => setTimeout(closeMobileMenu, 300));
    });
    
    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (window.innerWidth > 992) {
                closeMobileMenu();
                mobileMenuBtn.style.display = 'none';
            } else {
                mobileMenuBtn.style.display = 'block';
            }
        }, 250);
    });
    
    // Add animation styles if not exists
    if (!document.querySelector('#slideInAnimation')) {
        const style = document.createElement('style');
        style.id = 'slideInAnimation';
        style.textContent = `
            @keyframes slideInFromTop {
                from {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    mobileMenuInitialized = true;
    console.log('✅ Mobile menu initialized successfully');
}


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
                        Toast.error('Ukuran file maksimal 5MB', 'Upload Error');
                        this.value = '';
                        return;
                    }
                    
                    // Validate file type
                    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
                    if (!validTypes.includes(file.type)) {
                        Toast.error('Format file harus JPG, PNG, atau GIF', 'Upload Error');
                        this.value = '';
                        return;
                    }
                    
                    // Show preview
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewElement.innerHTML = `
                            <img src="${e.target.result}" alt="Preview" style="max-width: 100%; height: auto; border-radius: 8px;">
                            <p class="mt-10">${file.name} (${AppUtils.formatFileSize(file.size)})</p>
                        `;
                    };
                    reader.readAsDataURL(file);
                    
                    Toast.success('File berhasil dipilih', 'Upload');
                }
            });
        }
    });
}

// ==================== TOOLTIPS ====================

function initializeTooltips() {
    // Tooltips handled by CSS [data-tooltip] attribute
    // No additional JavaScript needed
}

// ==================== DATA TABLES ====================

function initializeDataTables() {
    const tables = document.querySelectorAll('table[data-sortable]');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th[data-sort]');
        
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const column = this.dataset.sort;
                sortTable(table, column);
            });
        });
    });
}

function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aValue = a.querySelector(`td[data-${column}]`)?.textContent || '';
        const bValue = b.querySelector(`td[data-${column}]`)?.textContent || '';
        return aValue.localeCompare(bValue);
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// ==================== CHARTS ====================

function initializeCharts() {
    // Chart initialization
    if (typeof Chart !== 'undefined') {
        // Set default chart options
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = '#64748b';
        
        // Find all canvas elements with data-chart attribute
        document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
            const chartType = canvas.dataset.chartType || 'line';
            const chartData = canvas.dataset.chartData;
            
            if (chartData) {
                try {
                    const data = JSON.parse(chartData);
                    new Chart(canvas, {
                        type: chartType,
                        data: data,
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: {
                                    position: 'top',
                                },
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    grid: {
                                        color: 'rgba(0, 0, 0, 0.1)'
                                    }
                                }
                            }
                        }
                    });
                } catch (e) {
                    console.error('Chart data parse error:', e);
                }
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
        
        const response = await fetch(endpoint, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
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
        setTimeout(() => hidePageLoader(loader), 3000);
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
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});

// ==================== MODAL FUNCTIONS ====================

function showSystemInfo() {
    const modal = document.getElementById('systemInfoModal');
    if (modal) {
        modal.classList.add('show');
        modal.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }
}

// ==================== GOOGLE SHEETS SYNC ====================

function syncWithGoogleSheets() {
    if (!confirm('Sync data dari Google Sheets ke database lokal?')) {
        return;
    }
    
    const btn = event.target;
    const originalText = btn.innerHTML;
    
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
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function refreshData() {
    window.location.reload();
}

function showRawData() {
    console.log('Monthly Reports:', window.monthlyReports || 'Not available');
    console.log('Yearly Stats:', window.yearlyStats || 'Not available');
    Toast.info('Data logged to console. Press F12 to view.', 'Debug Info');
}

function exportMonthlyToCSV() {
    if (!window.monthlyReports || window.monthlyReports.length === 0) {
        Toast.warning('Tidak ada data untuk diekspor', 'Export');
        return;
    }
    exportToCSV(window.monthlyReports, `laporan_bulanan_${new Date().toISOString().slice(0,7)}.csv`);
}

function printTable() {
    window.print();
}

function viewReport(reportId) {
    Toast.info(`Viewing report #${reportId}. Feature coming soon!`, 'Info');
}