/**
 * Leafanoo Shopify OS 2.0 Theme Core JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
  initStickyHeader();
  initMobileNav();
  initAnnouncementDismiss();
  initAjaxAddToCart();
  initQuantitySteppers();
});

// Sticky Header Observer
function initStickyHeader() {
  const header = document.querySelector('.site-header');
  if (!header) return;

  const observer = new IntersectionObserver(([entry]) => {
    header.classList.toggle('is-scrolled', !entry.isIntersecting);
  }, { threshold: 1 });

  const dummy = document.createElement('div');
  dummy.style.height = '1px';
  document.body.prepend(dummy);
  observer.observe(dummy);
}

// Mobile Navigation Toggle
function initMobileNav() {
  const toggleBtn = document.querySelector('.mobile-menu-toggle');
  const navDrawer = document.getElementById('MobileNavDrawer');
  const closeBtn = document.querySelector('.mobile-nav-close');
  const backdrop = document.querySelector('.mobile-nav-backdrop');

  if (!toggleBtn || !navDrawer) return;

  function openNav() {
    navDrawer.style.display = 'block';
    setTimeout(() => {
      navDrawer.classList.add('is-open');
    }, 10);
    document.body.style.overflow = 'hidden';
  }

  function closeNav() {
    navDrawer.classList.remove('is-open');
    setTimeout(() => {
      navDrawer.style.display = 'none';
    }, 300);
    document.body.style.overflow = '';
  }

  toggleBtn.addEventListener('click', openNav);
  if (closeBtn) closeBtn.addEventListener('click', closeNav);
  if (backdrop) backdrop.addEventListener('click', closeNav);
}

// Announcement Bar Dismiss
function initAnnouncementDismiss() {
  const bar = document.querySelector('.announcement-bar');
  const closeBtn = document.querySelector('.announcement-bar__close');
  if (!bar || !closeBtn) return;

  const dismissed = localStorage.getItem('leafanoo_announcement_dismissed');
  if (dismissed === 'true') {
    bar.style.display = 'none';
  }

  closeBtn.addEventListener('click', () => {
    bar.style.display = 'none';
    localStorage.setItem('leafanoo_announcement_dismissed', 'true');
  });
}

// AJAX Add to Cart
function initAjaxAddToCart() {
  document.addEventListener('submit', function(e) {
    const form = e.target.closest('form[action*="/cart/add"]');
    if (!form) return;

    e.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalHTML = submitBtn ? submitBtn.innerHTML : '';

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = 'Adding...';
    }

    const formData = new FormData(form);

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: formData
    })
    .then(res => res.json())
    .then(data => {
      if (data.status && data.status >= 400) {
        alert(data.description || 'Unable to add product to cart.');
      } else {
        // Dispatch event for cart drawer, then update count
        document.dispatchEvent(new CustomEvent('cart:item-added', { detail: data }));
        // Update cart count badges immediately
        fetch('/cart.js')
          .then(r => r.json())
          .then(cart => {
            document.querySelectorAll('.cart-count-badge').forEach(el => {
              el.textContent = cart.item_count;
            });
          });
      }
    })
    .catch(err => {
      console.error('Cart add error:', err);
      // Fallback: submit the form normally
      form.submit();
    })
    .finally(() => {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
      }
    });
  });
}

// Quantity Input Steppers
function initQuantitySteppers() {
  document.addEventListener('click', function(e) {
    const minusBtn = e.target.closest('.qty-minus');
    const plusBtn = e.target.closest('.qty-plus');

    if (!minusBtn && !plusBtn) return;

    const wrapper = (minusBtn || plusBtn).closest('.quantity-input-wrapper');
    if (!wrapper) return;

    const input = wrapper.querySelector('input[type="number"]');
    if (!input) return;

    let val = parseInt(input.value, 10) || 1;
    if (minusBtn) {
      if (val > 1) input.value = val - 1;
    } else if (plusBtn) {
      input.value = val + 1;
    }

    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
}
