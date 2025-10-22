/**
 * Budget Alerts Form Enhancements
 * Handles "Others" category selection, custom input, validation, and safe AJAX submission
 */

document.addEventListener('DOMContentLoaded', function () {
  // Elements
  const categoryChoiceSelect = document.getElementById('id_category_choice');
  const customCategoryInput = document.getElementById('id_custom_category');
  const thresholdInput = document.querySelector('input[name="threshold_percent"]');
  const thresholdValueDisplay = document.getElementById('threshold_value_display');

  // Initialize "Others" toggle
  if (categoryChoiceSelect && customCategoryInput) {
    toggleCustomCategory();
    categoryChoiceSelect.addEventListener('change', toggleCustomCategory);
  }

  // Initialize threshold display
  if (thresholdInput && thresholdValueDisplay) {
    updateThresholdValue(thresholdInput.value);
    thresholdInput.addEventListener('input', function () {
      updateThresholdValue(this.value);
    });
  }

  // Add listener for custom category input
  const customInput = document.getElementById('id_custom_category');
  if (customInput) {
    customInput.addEventListener('input', warnSimilarCategory);
    customInput.addEventListener('blur', warnSimilarCategory);
  }

  // Initialize progress bars
  initializeBudgetProgressBars();

  // Attach secure form submit handler (AJAX + duplicate protection)
  const form = document.getElementById('budgetAlertForm');
  if (form) setupAjaxFormSubmit(form);
});

/**
 * Safe AJAX Form Submit Handler
 * Prevents duplicate submits, validates, and only shows success after server confirmation
 */
function setupAjaxFormSubmit(form) {
  let saving = false;
  const submitBtn = form.querySelector('button[type="submit"]');

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    if (saving) return; // Prevent double-click submissions

    if (!validateBudgetAlertForm()) return; // Client-side validation

    saving = true;
    submitBtn.disabled = true;

    const url = form.action || window.location.href;
    const formData = new FormData(form);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData,
      });

      let data = null;
      try {
        data = await res.json();
      } catch (err) {
        /* ignore non-JSON responses */
      }

      if (res.ok) {
        const msg = data?.message || '✅ Budget alert created successfully!';
        showToast(msg, 'success');
        setTimeout(() => window.location.reload(), 1000);
      } else {
        const msg =
          data?.message ||
          data?.detail ||
          '⚠️ Failed to create budget alert. Please try again.';
        showToast(msg, 'warning');
      }
    } catch (err) {
      showToast('❌ Network error — could not reach server.', 'danger');
      console.error('Form submission failed:', err);
    } finally {
      saving = false;
      submitBtn.disabled = false;
    }
  });
}

/**
 * Simple Bootstrap Toast/Alert fallback
 */
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x shadow-sm`;
  toast.style.zIndex = 1080;
  toast.style.marginTop = '1rem';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

/**
 * Toggles visibility of the custom category input
 */
function toggleCustomCategory() {
  const categoryChoiceSelect = document.getElementById('id_category_choice');
  const customCategoryInput = document.getElementById('id_custom_category');
  const customCategoryGroup =
    customCategoryInput?.closest('.mb-3') ||
    customCategoryInput?.closest('.form-group');

  if (!categoryChoiceSelect || !customCategoryInput) return;

  const selectedValue = categoryChoiceSelect.value;

  if (selectedValue === 'Others') {
    customCategoryInput.style.display = 'block';
    if (customCategoryGroup) customCategoryGroup.style.display = 'block';
    customCategoryInput.required = true;
    customCategoryInput.focus();
  } else {
    customCategoryInput.style.display = 'none';
    if (customCategoryGroup) customCategoryGroup.style.display = 'none';
    customCategoryInput.required = false;
    customCategoryInput.value = '';
  }
}

/**
 * Updates threshold display
 */
function updateThresholdValue(value) {
  const display = document.getElementById('threshold_value_display');
  if (display) display.textContent = value + '%';
}

/**
 * Validate form fields
 */
function validateBudgetAlertForm() {
  const categoryChoice = document.getElementById('id_category_choice')?.value;
  const customCategory = document.getElementById('id_custom_category')?.value;
  const amountLimit = document.getElementById('id_amount_limit')?.value;
  const thresholdPercent = document.querySelector(
    'input[name="threshold_percent"]'
  )?.value;

  if (!categoryChoice) {
    showToast('⚠️ Please select a category.', 'warning');
    return false;
  }

  if (categoryChoice === 'Others' && !customCategory?.trim()) {
    showToast('⚠️ Please enter a custom category name.', 'warning');
    document.getElementById('id_custom_category')?.focus();
    return false;
  }

  if (!amountLimit || parseFloat(amountLimit) <= 0) {
    showToast('⚠️ Please enter a valid budget limit greater than zero.', 'warning');
    document.getElementById('id_amount_limit')?.focus();
    return false;
  }

  if (parseFloat(amountLimit) > 999999999.99) {
    showToast('⚠️ Budget limit too large. Maximum is ₱999,999,999.99', 'warning');
    document.getElementById('id_amount_limit')?.focus();
    return false;
  }

  if (
    !thresholdPercent ||
    parseInt(thresholdPercent) < 10 ||
    parseInt(thresholdPercent) > 100
  ) {
    showToast('⚠️ Threshold must be between 10% and 100%.', 'warning');
    return false;
  }

  return true;
}

/**
 * Warn for similar categories
 */
function warnSimilarCategory() {
  const categoryChoiceSelect = document.getElementById('id_category_choice');
  const customCategoryInput = document.getElementById('id_custom_category');
  if (!categoryChoiceSelect || !customCategoryInput) return;

  const selectedValue = categoryChoiceSelect.value;
  const customValue = customCategoryInput.value;
  const warningDiv = document.getElementById('category_warning');

  if (selectedValue === 'Others' && customValue) {
    const majorCategories = [
      'Food',
      'Transport',
      'Leisure',
      'Bills',
      'School Supplies',
      'Shopping',
      'Healthcare',
      'Entertainment',
    ];

    const match = findMatchingMajorCategory(customValue, majorCategories);
    if (match) {
      const warningMsg = `💡 Tip: "${customValue}" will be automatically categorized as "${match}"`;
      if (warningDiv) {
        warningDiv.textContent = warningMsg;
        warningDiv.style.display = 'block';
        warningDiv.className = 'alert alert-info mt-2';
      }
    } else if (warningDiv) {
      warningDiv.style.display = 'none';
    }
  } else if (warningDiv) {
    warningDiv.style.display = 'none';
  }
}

/**
 * Helpers for category comparison and display
 */
function normalizeCategoryName(categoryName) {
  return categoryName.trim().toLowerCase().replace(/\s+/g, ' ');
}

function findMatchingMajorCategory(customName, majorCategories) {
  const normalizedCustom = normalizeCategoryName(customName);
  for (const major of majorCategories) {
    const normalizedMajor = normalizeCategoryName(major);
    if (
      normalizedCustom === normalizedMajor ||
      normalizedCustom.includes(normalizedMajor) ||
      normalizedMajor.includes(normalizedCustom)
    ) {
      return major;
    }
  }
  return null;
}

/**
 * Initialize progress bars for budget alerts
 */
function initializeBudgetProgressBars() {
  const progressBars = document.querySelectorAll('.budget-progress-bar');

  progressBars.forEach((bar) => {
    const percentUsed = parseFloat(bar.dataset.percentUsed || 0);
    const threshold = parseFloat(bar.dataset.threshold || 80);
    bar.style.width = percentUsed + '%';
    const colorClass = getBudgetColorClass(percentUsed, threshold);
    bar.className = `progress-bar bg-${colorClass} budget-progress-bar`;
    bar.classList.add('progress-bar-striped');
    if (percentUsed >= threshold) bar.classList.add('progress-bar-animated');
  });
}

function getBudgetColorClass(percentUsed, threshold) {
  if (percentUsed >= 100) return 'danger';
  if (percentUsed >= threshold) return 'warning';
  if (percentUsed >= threshold * 0.7) return 'info';
  return 'success';
}

/**
 * Export functions globally (optional)
 */
window.BudgetAlertsJS = {
  toggleCustomCategory,
  updateThresholdValue,
  validateBudgetAlertForm,
  normalizeCategoryName,
  findMatchingMajorCategory,
  warnSimilarCategory,
  initializeBudgetProgressBars,
};
