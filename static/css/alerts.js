// Keep the slider label (e.g., "80%") in sync with the range input value.
(function () {
  const slider = document.getElementById('trigger');
  const out = document.getElementById('triggerValue');

  if (!slider || !out) return;

  const update = () => {
    out.textContent = (slider.value || 0) + '%';
  };

  slider.addEventListener('input', update);
  update();
})();

// Lightweight client-side validation that mirrors your user stories.
// - Amount required
// - Category required
// Let Django handle all real validation and saving; we only block obvious empties.
(function () {
  const form = document.querySelector('form[method="post"]');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    const amount = document.getElementById('amountLimit');
    const category = document.getElementById('category');

    let ok = true;

    // Amount Required (must be > 0)
    if (!amount || !amount.value || Number(amount.value) <= 0) {
      if (amount) amount.classList.add('is-invalid');
      ok = false;
    } else {
      amount.classList.remove('is-invalid');
    }

    // Category Required (must have a value)
    if (!category || !category.value) {
      if (category) category.classList.add('is-invalid');
      ok = false;
    } else {
      category.classList.remove('is-invalid');
    }

    // If invalid, stop the submit. Otherwise, let Django handle it.
    if (!ok) {
      e.preventDefault();
      e.stopPropagation();
    }
  });
})();

document.addEventListener('DOMContentLoaded', function() {
  // Edit button handler
  document.querySelectorAll('.edit-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      populateEditModal(
        btn.getAttribute('data-id'),
        btn.getAttribute('data-amount'),
        btn.getAttribute('data-category'),
        btn.getAttribute('data-threshold')
      );
    });
  });

  // Delete button handler
  document.querySelectorAll('.delete-btn').forEach(function(btn) {
    btn.addEventListener('click', function(event) {
      event.preventDefault();
      if (confirm("Are you sure you want to delete this alert?")) {
        window.location.href = btn.getAttribute('data-url');
      }
    });
  });
});
