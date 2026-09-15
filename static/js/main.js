/**
 * Companio - Core JavaScript
 * Theme switcher, Font scaling, Accessibility tools, and Interactive UX
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initAccessibilityToolbar();
  initToastSystem();
});

/* Theme Switcher (Dark / Light Mode) */
function initTheme() {
  const savedTheme = localStorage.getItem('companio-theme') || 'light';
  document.documentElement.setAttribute('data-bs-theme', savedTheme);
  updateThemeIcon(savedTheme);

  const themeToggleButtons = document.querySelectorAll('.theme-toggle-btn');
  themeToggleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-bs-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-bs-theme', newTheme);
      localStorage.setItem('companio-theme', newTheme);
      updateThemeIcon(newTheme);
      showToast(`Switched to ${newTheme} mode`, 'info');
    });
  });
}

function updateThemeIcon(theme) {
  const themeIcons = document.querySelectorAll('.theme-toggle-icon');
  themeIcons.forEach(icon => {
    if (theme === 'dark') {
      icon.className = 'theme-toggle-icon fas fa-sun text-warning';
    } else {
      icon.className = 'theme-toggle-icon fas fa-moon text-dark';
    }
  });
}

/* Accessibility Toolbar Logic */
let currentFontSize = 100; // Percentage

function initAccessibilityToolbar() {
  const fontIncreaseBtn = document.getElementById('btn-font-increase');
  const fontDecreaseBtn = document.getElementById('btn-font-decrease');
  const fontResetBtn = document.getElementById('btn-font-reset');
  const contrastToggleBtn = document.getElementById('btn-contrast-toggle');
  const ttsToggleBtn = document.getElementById('btn-tts-toggle');

  if (fontIncreaseBtn) {
    fontIncreaseBtn.addEventListener('click', () => {
      if (currentFontSize < 140) {
        currentFontSize += 10;
        document.body.style.fontSize = `${currentFontSize}%`;
        showToast(`Font size increased to ${currentFontSize}%`, 'info');
      }
    });
  }

  if (fontDecreaseBtn) {
    fontDecreaseBtn.addEventListener('click', () => {
      if (currentFontSize > 90) {
        currentFontSize -= 10;
        document.body.style.fontSize = `${currentFontSize}%`;
        showToast(`Font size decreased to ${currentFontSize}%`, 'info');
      }
    });
  }

  if (fontResetBtn) {
    fontResetBtn.addEventListener('click', () => {
      currentFontSize = 100;
      document.body.style.fontSize = '100%';
      showToast('Font size reset to normal', 'info');
    });
  }

  if (contrastToggleBtn) {
    contrastToggleBtn.addEventListener('click', () => {
      document.body.classList.toggle('high-contrast');
      const isHighContrast = document.body.classList.contains('high-contrast');
      showToast(isHighContrast ? 'High Contrast Mode Enabled' : 'High Contrast Mode Disabled', 'info');
    });
  }

  if (ttsToggleBtn) {
    ttsToggleBtn.addEventListener('click', () => {
      speakPageTitle();
    });
  }
}

/* Text to Speech / Screen Reader Simulation */
function speakPageTitle() {
  if ('speechSynthesis' in window) {
    const pageTitle = document.querySelector('h1')?.innerText || document.title;
    const utterance = new SpeechSynthesisUtterance(`Currently viewing: ${pageTitle}`);
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
    showToast(`Reading out page title: ${pageTitle}`, 'success');
  } else {
    showToast('Text-to-Speech is not supported in this browser', 'warning');
  }
}

/* Toast Notifications Helper */
function initToastSystem() {
  if (!document.getElementById('toast-container')) {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
  }
}

// AJAX handler for admin action forms to avoid full page reload
document.addEventListener('submit', function(event) {
  console.log('Submit event captured', event.target);
  const form = event.target;
  // Trigger AJAX for forms marked with admin-action-form (any method)
  const isAdminForm = form.classList.contains('admin-action-form');
  if (isAdminForm) {
    event.preventDefault();
    event.stopPropagation();
    // Custom confirmation if data-confirm attribute is present
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
      return; // user cancelled
    }
    const url = form.action;
    const method = form.method ? form.method.toUpperCase() : 'GET';
    const formData = new FormData(form);
    // Add CSRF token for POST requests
    if (method === 'POST') {
      function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
      }
      const csrftoken = getCookie('csrfmiddlewaretoken') || getCookie('csrftoken');
      if (csrftoken) {
        formData.append('csrfmiddlewaretoken', csrftoken);
      }
    }
    fetch(url, {
      method: method,
      body: method === 'GET' ? null : formData,
      credentials: 'same-origin'
    })
    .then(response => {
      if (response.redirected) {
        // Follow redirect to get final page content
        return fetch(response.url, {credentials: 'same-origin'});
      }
      return response;
    })
    .then(resp => resp.text())
      .then(html => {
        // Simple feedback: show success toast
        showToast('Action completed successfully.', 'success');
        // Update the row UI directly (toggle status badge and button) without full table reload
        const row = form.closest('tr');
        if (row) {
          const statusBadge = row.querySelector('td:nth-child(6) .badge');
          const actionBtn = row.querySelector('td.text-end button.btn');
          if (statusBadge && actionBtn) {
            // Determine current state from button class
            const isActive = actionBtn.classList.contains('btn-outline-danger'); // currently active, will become suspended
            // Update badge
            statusBadge.className = isActive ? 'badge bg-danger' : 'badge bg-success';
            statusBadge.textContent = isActive ? 'Suspended' : 'Active';
            // Update button appearance and title
            if (isActive) {
              actionBtn.className = 'btn btn-sm btn-outline-success';
              actionBtn.title = 'Activate Account';
              const icon = actionBtn.querySelector('i.fas');
              if (icon) { icon.className = 'fas fa-check'; }
            } else {
              actionBtn.className = 'btn btn-sm btn-outline-danger';
              actionBtn.title = 'Suspend Account';
              const icon = actionBtn.querySelector('i.fas');
              if (icon) { icon.className = 'fas fa-ban'; }
            }
          }
        }
      })
      .catch(error => {
        console.error('Admin action error:', error);
        showToast('Action failed. Check console for details.', 'danger');
      });
    return;
  }

  // GET filter form handling (no class needed, just GET method and inside admin page)
  const isGetForm = form.method && form.method.toUpperCase() === 'GET';
  const isInAdmin = form.closest('div.card') !== null;
  if (isGetForm && isInAdmin) {
    event.preventDefault();
    const url = form.action + '?' + new URLSearchParams(new FormData(form)).toString();
    fetch(url, {method: 'GET', credentials: 'same-origin'})
      .then(resp => resp.text())
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newTbody = doc.querySelector('table tbody');
        const oldTbody = document.querySelector('table tbody');
        if (newTbody && oldTbody) {
          oldTbody.replaceWith(newTbody);
          showToast('Table updated.', 'success');
        } else {
          showToast('Could not update table.', 'warning');
        }
      })
      .catch(err => {
        console.error('Filter AJAX error:', err);
        showToast('Filter update failed.', 'danger');
      });
  }
});

// Helper to refresh the current table via AJAX (used after POST actions)
function refreshTable() {
  // Use the current URL (including query parameters) to fetch updated table content
  const url = window.location.href;
  fetch(url, {method: 'GET', credentials: 'same-origin'})
    .then(resp => resp.text())
    .then(html => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const newTbody = doc.querySelector('table tbody');
      const oldTbody = document.querySelector('table tbody');
      if (newTbody && oldTbody) {
        oldTbody.replaceWith(newTbody);
        showToast('Table refreshed.', 'success');
      } else {
        showToast('Could not refresh table.', 'warning');
      }
    })
    .catch(err => {
      console.error('Table refresh error:', err);
      showToast('Table refresh failed.', 'danger');
    });
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toastId = 'toast-' + Date.now();
  const bgClass = type === 'success' ? 'bg-success text-white' : 
                  type === 'warning' ? 'bg-warning text-dark' : 
                  type === 'danger' ? 'bg-danger text-white' : 'bg-primary text-white';

  const html = `
    <div id="${toastId}" class="toast align-items-center ${bgClass} border-0 show" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">
          <i class="fas fa-info-circle me-2"></i> ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;

  container.insertAdjacentHTML('beforeend', html);
  setTimeout(() => {
    const el = document.getElementById(toastId);
    if (el) el.remove();
  }, 4000);
}
