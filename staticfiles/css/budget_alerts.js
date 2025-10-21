/**
 * Budget Alerts Form Enhancements
 * Handles "Others" category selection and custom category input
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const categoryChoiceSelect = document.getElementById('id_category_choice');
    const customCategoryInput = document.getElementById('id_custom_category');
    const thresholdInput = document.querySelector('input[name="threshold_percent"]');
    const thresholdValueDisplay = document.getElementById('threshold_value_display');

    // Initialize
    if (categoryChoiceSelect && customCategoryInput) {
        // Set initial state
        toggleCustomCategory();
        
        // Add event listener for category selection changes
        categoryChoiceSelect.addEventListener('change', toggleCustomCategory);
    }

    // Initialize threshold display
    if (thresholdInput && thresholdValueDisplay) {
        updateThresholdValue(thresholdInput.value);
        thresholdInput.addEventListener('input', function() {
            updateThresholdValue(this.value);
        });
    }
});

/**
 * Toggles the visibility of the custom category input field
 * Shows when "Others" is selected, hides otherwise
 */
function toggleCustomCategory() {
    const categoryChoiceSelect = document.getElementById('id_category_choice');
    const customCategoryInput = document.getElementById('id_custom_category');
    const customCategoryGroup = customCategoryInput?.closest('.mb-3') || customCategoryInput?.closest('.form-group');

    if (!categoryChoiceSelect || !customCategoryInput) {
        return;
    }

    const selectedValue = categoryChoiceSelect.value;

    if (selectedValue === 'Others') {
        // Show custom input
        customCategoryInput.style.display = 'block';
        if (customCategoryGroup) {
            customCategoryGroup.style.display = 'block';
        }
        customCategoryInput.required = true;
        customCategoryInput.focus();
    } else {
        // Hide custom input
        customCategoryInput.style.display = 'none';
        if (customCategoryGroup) {
            customCategoryGroup.style.display = 'none';
        }
        customCategoryInput.required = false;
        customCategoryInput.value = '';  // Clear the value
    }
}

/**
 * Updates the threshold percentage display value
 * @param {number} value - The threshold percentage value (10-100)
 */
function updateThresholdValue(value) {
    const display = document.getElementById('threshold_value_display');
    if (display) {
        display.textContent = value + '%';
    }
}

/**
 * Validates the budget alert form before submission
 * Checks for required fields and valid amounts
 * @returns {boolean} - True if valid, false otherwise
 */
function validateBudgetAlertForm() {
    const categoryChoice = document.getElementById('id_category_choice')?.value;
    const customCategory = document.getElementById('id_custom_category')?.value;
    const amountLimit = document.getElementById('id_amount_limit')?.value;
    const thresholdPercent = document.querySelector('input[name="threshold_percent"]')?.value;

    // Check category
    if (!categoryChoice) {
        alert('⚠️ Please select a category.');
        return false;
    }

    // Check custom category if "Others" selected
    if (categoryChoice === 'Others' && !customCategory?.trim()) {
        alert('⚠️ Please enter a custom category name.');
        document.getElementById('id_custom_category')?.focus();
        return false;
    }

    // Check amount limit
    if (!amountLimit || parseFloat(amountLimit) <= 0) {
        alert('⚠️ Please enter a valid budget limit greater than zero.');
        document.getElementById('id_amount_limit')?.focus();
        return false;
    }

    // Check if amount is too large
    if (parseFloat(amountLimit) > 999999999.99) {
        alert('⚠️ Budget limit is too large. Maximum is ₱999,999,999.99');
        document.getElementById('id_amount_limit')?.focus();
        return false;
    }

    // Check threshold
    if (!thresholdPercent || parseInt(thresholdPercent) < 10 || parseInt(thresholdPercent) > 100) {
        alert('⚠️ Threshold must be between 10% and 100%.');
        return false;
    }

    return true;
}

/**
 * Confirms deletion of a budget alert
 * @param {string} categoryName - The category name to delete
 * @returns {boolean} - True if confirmed, false otherwise
 */
function confirmDeleteAlert(categoryName) {
    return confirm(`Are you sure you want to delete the budget alert for "${categoryName}"?\n\nThis action cannot be undone.`);
}

/**
 * Formats currency value for display
 * @param {number} amount - The amount to format
 * @returns {string} - Formatted currency string (e.g., "₱1,234.56")
 */
function formatCurrency(amount) {
    return '₱' + parseFloat(amount).toLocaleString('en-PH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Calculates and displays budget usage percentage
 * @param {number} currentSpending - Current amount spent
 * @param {number} budgetLimit - Total budget limit
 * @returns {number} - Percentage used (0-100)
 */
function calculateBudgetUsage(currentSpending, budgetLimit) {
    if (budgetLimit <= 0) return 0;
    return Math.min((currentSpending / budgetLimit * 100), 100);
}

/**
 * Gets the appropriate color class for budget usage
 * @param {number} percentUsed - Percentage of budget used
 * @param {number} threshold - Alert threshold percentage
 * @returns {string} - Bootstrap color class (success/warning/danger)
 */
function getBudgetColorClass(percentUsed, threshold) {
    if (percentUsed >= 100) return 'danger';
    if (percentUsed >= threshold) return 'warning';
    if (percentUsed >= threshold * 0.7) return 'info';
    return 'success';
}

/**
 * Normalizes category name for comparison
 * Converts to lowercase and removes extra spaces
 * @param {string} categoryName - The category name to normalize
 * @returns {string} - Normalized category name
 */
function normalizeCategoryName(categoryName) {
    return categoryName.trim().toLowerCase().replace(/\s+/g, ' ');
}

/**
 * Checks if a custom category name matches a major category
 * @param {string} customName - The custom category name entered
 * @param {Array<string>} majorCategories - List of major category names
 * @returns {string|null} - Matching major category or null
 */
function findMatchingMajorCategory(customName, majorCategories) {
    const normalizedCustom = normalizeCategoryName(customName);
    
    for (const major of majorCategories) {
        const normalizedMajor = normalizeCategoryName(major);
        
        // Exact match
        if (normalizedCustom === normalizedMajor) {
            return major;
        }
        
        // Custom contains major
        if (normalizedCustom.includes(normalizedMajor)) {
            return major;
        }
        
        // Major contains custom
        if (normalizedMajor.includes(normalizedCustom)) {
            return major;
        }
    }
    
    return null;
}

/**
 * Shows a warning if custom category is similar to a major category
 */
function warnSimilarCategory() {
    const categoryChoiceSelect = document.getElementById('id_category_choice');
    const customCategoryInput = document.getElementById('id_custom_category');
    
    if (!categoryChoiceSelect || !customCategoryInput) return;
    
    const selectedValue = categoryChoiceSelect.value;
    const customValue = customCategoryInput.value;
    
    if (selectedValue === 'Others' && customValue) {
        const majorCategories = [
            'Food', 'Transport', 'Leisure', 'Bills', 
            'School Supplies', 'Shopping', 'Healthcare', 'Entertainment'
        ];
        
        const match = findMatchingMajorCategory(customValue, majorCategories);
        
        if (match) {
            const warningMsg = `💡 Tip: "${customValue}" will be automatically categorized as "${match}"`;
            const warningDiv = document.getElementById('category_warning');
            
            if (warningDiv) {
                warningDiv.textContent = warningMsg;
                warningDiv.style.display = 'block';
                warningDiv.className = 'alert alert-info mt-2';
            } else {
                console.log(warningMsg);
            }
        } else {
            const warningDiv = document.getElementById('category_warning');
            if (warningDiv) {
                warningDiv.style.display = 'none';
            }
        }
    }
}

// Add event listener for custom category input
document.addEventListener('DOMContentLoaded', function() {
    const customCategoryInput = document.getElementById('id_custom_category');
    if (customCategoryInput) {
        customCategoryInput.addEventListener('input', warnSimilarCategory);
        customCategoryInput.addEventListener('blur', warnSimilarCategory);
    }
});

/**
 * Initialize progress bars for budget alerts
 * Updates progress bar widths and colors based on usage
 */
function initializeBudgetProgressBars() {
    const progressBars = document.querySelectorAll('.budget-progress-bar');
    
    progressBars.forEach(bar => {
        const percentUsed = parseFloat(bar.dataset.percentUsed || 0);
        const threshold = parseFloat(bar.dataset.threshold || 80);
        
        // Set width
        bar.style.width = percentUsed + '%';
        
        // Set color
        const colorClass = getBudgetColorClass(percentUsed, threshold);
        bar.className = `progress-bar bg-${colorClass} budget-progress-bar`;
        
        // Add animation
        bar.classList.add('progress-bar-striped');
        if (percentUsed >= threshold) {
            bar.classList.add('progress-bar-animated');
        }
    });
}

// Initialize progress bars on page load
document.addEventListener('DOMContentLoaded', initializeBudgetProgressBars);

/**
 * Export functions for use in other scripts
 */
window.BudgetAlertsJS = {
    toggleCustomCategory,
    updateThresholdValue,
    validateBudgetAlertForm,
    confirmDeleteAlert,
    formatCurrency,
    calculateBudgetUsage,
    getBudgetColorClass,
    normalizeCategoryName,
    findMatchingMajorCategory,
    warnSimilarCategory,
    initializeBudgetProgressBars
};
