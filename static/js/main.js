// Main JavaScript functionality for Invoice Management System

document.addEventListener('DOMContentLoaded', function() {
    setupPageTransitions();
    initializePage();
    initAlertAutoHide();
});

function setupPageTransitions() {
    const body = document.body;
    body.classList.add('page-transition');
    
    // Use requestAnimationFrame for smoother animation start
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            body.classList.add('page-loaded');
        });
    });

    const triggerExit = (callback) => {
        body.classList.remove('page-loaded');
        body.classList.add('page-transition-exit');
        setTimeout(callback, 400);
    };

    const shouldIgnoreLink = (link) => {
        const href = link.getAttribute('href');
        return (
            !href ||
            href.startsWith('#') ||
            link.hasAttribute('data-no-transition') ||
            (link.target && link.target !== '_self')
        );
    };

    document.querySelectorAll('a[href]').forEach(link => {
        link.addEventListener('click', function(event) {
            if (shouldIgnoreLink(link)) {
                return;
            }
            event.preventDefault();
            triggerExit(() => {
                window.location.href = link.href;
            });
        });
    });

    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(event) {
            if (form.dataset.transitioning === 'true') {
                return;
            }
            form.dataset.transitioning = 'true';
            event.preventDefault();
            triggerExit(() => form.submit());
        });
    });

    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            body.classList.remove('page-transition-exit');
            body.classList.add('page-loaded');
        }
    });
}

function initializePage() {
    // User menu dropdown toggle
    const toggle = document.getElementById('userToggle');
    const dropdown = document.getElementById('userDropdown');
    if (toggle && dropdown) {
        toggle.addEventListener('click', function (e) {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });
        document.addEventListener('click', function () {
            dropdown.classList.remove('show');
        });
    }
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.innerHTML = `
        ${message}
        <button class="alert-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Insert at the top of main content
    const main = document.querySelector('main');
    if (main) {
        main.insertBefore(alertDiv, main.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Form validation
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    return isValid;
}

// Add error styling for invalid fields
const style = document.createElement('style');
style.textContent = `
    .form-input.error {
        border-color: #ef4444;
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
    }
`;
document.head.appendChild(style);

function initAlertAutoHide() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 300);
            }
        }, 5000);
    });
}

// Add smooth transitions for alerts
const alertStyle = document.createElement('style');
alertStyle.textContent = `
    .alert {
        transition: opacity 0.3s ease;
    }
`;
document.head.appendChild(alertStyle);
