/**
 * Leafanoo Cart Drawer JavaScript
 * Handles slide-out, AJAX increment/decrement/remove, and 50% deposit calculation.
 */

class CartDrawer {
  constructor() {
    this.drawer = document.getElementById('CartDrawer');
    if (!this.drawer) return;

    this.container = this.drawer.querySelector('.cart-drawer__container');
    this.backdrop = this.drawer.querySelector('.cart-drawer__backdrop');
    this.closeBtn = this.drawer.querySelector('.cart-drawer-close');
    this.itemsContainer = document.getElementById('CartDrawerItems');
    this.isUpdating = false;

    this.bindEvents();
  }

  bindEvents() {
    // Open triggers
    document.addEventListener('click', (e) => {
      const trigger = e.target.closest('[data-cart-drawer-trigger]');
      if (trigger) {
        e.preventDefault();
        this.open();
      }
    });

    // Listen to custom cart events
    document.addEventListener('cart:item-added', () => {
      this.refresh().then(() => this.open());
    });

    // Close handlers
    if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.close());
    if (this.backdrop) this.backdrop.addEventListener('click', () => this.close());

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen()) this.close();
    });

    // Delegation for Increment, Decrement, and Remove buttons
    if (this.drawer) {
      this.drawer.addEventListener('click', async (e) => {
        // Increment
        const incBtn = e.target.closest('[data-action="increment"]');
        if (incBtn) {
          e.preventDefault();
          const key = incBtn.getAttribute('data-key');
          const currentQty = parseInt(incBtn.getAttribute('data-current-qty') || '1', 10);
          await this.changeQuantity(key, currentQty + 1);
          return;
        }

        // Decrement
        const decBtn = e.target.closest('[data-action="decrement"]');
        if (decBtn) {
          e.preventDefault();
          const key = decBtn.getAttribute('data-key');
          const currentQty = parseInt(decBtn.getAttribute('data-current-qty') || '1', 10);
          await this.changeQuantity(key, Math.max(0, currentQty - 1));
          return;
        }

        // Remove
        const rmBtn = e.target.closest('[data-cart-remove]');
        if (rmBtn) {
          e.preventDefault();
          const key = rmBtn.getAttribute('data-key');
          await this.changeQuantity(key, 0);
          return;
        }
      });
    }
  }

  isOpen() {
    return this.drawer && this.drawer.style.display !== 'none';
  }

  open() {
    if (!this.drawer) return;
    this.drawer.style.display = 'block';
    setTimeout(() => {
      if (this.container) this.container.style.transform = 'translateX(0)';
    }, 10);
    document.body.style.overflow = 'hidden';
  }

  close() {
    if (!this.drawer) return;
    if (this.container) this.container.style.transform = 'translateX(100%)';
    setTimeout(() => {
      this.drawer.style.display = 'none';
      document.body.style.overflow = '';
    }, 300);
  }

  async changeQuantity(key, newQty) {
    if (this.isUpdating || !key) return;
    this.isUpdating = true;
    if (this.itemsContainer) this.itemsContainer.style.opacity = '0.4';

    try {
      const res = await fetch('/cart/change.js', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          id: key,
          quantity: newQty
        })
      });

      if (res.ok) {
        await this.refresh();
      } else {
        console.error('Failed to update cart quantity:', await res.text());
      }
    } catch (err) {
      console.error('Error changing cart quantity:', err);
    } finally {
      this.isUpdating = false;
      if (this.itemsContainer) this.itemsContainer.style.opacity = '1';
    }
  }

  async refresh() {
    try {
      const res = await fetch('/cart.js');
      const cart = await res.json();
      this.updateCounts(cart.item_count);
      this.updateSubtotal(cart.total_price);

      // Re-fetch rendered cart-drawer section to update items & 50% deposit amounts
      const sectionRes = await fetch('/?section_id=cart-drawer');
      const text = await sectionRes.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(text, 'text/html');

      const newItems = doc.getElementById('CartDrawerItems');
      if (newItems && this.itemsContainer) {
        this.itemsContainer.innerHTML = newItems.innerHTML;
      }

      const newFooter = doc.querySelector('.cart-drawer__footer');
      const currentFooter = this.drawer.querySelector('.cart-drawer__footer');
      if (newFooter && currentFooter) {
        currentFooter.innerHTML = newFooter.innerHTML;
      }
    } catch (e) {
      console.error('Cart drawer refresh error:', e);
    }
  }

  updateCounts(count) {
    document.querySelectorAll('.cart-count-badge, .cart-drawer-count').forEach(el => {
      el.textContent = count;
    });
  }

  updateSubtotal(total) {
    const totalDollars = (total / 100).toFixed(2);
    const depositDollars = (total / 200).toFixed(2);

    document.querySelectorAll('.cart-drawer-subtotal').forEach(el => {
      el.textContent = `$${totalDollars}`;
    });

    document.querySelectorAll('.cart-drawer-deposit').forEach(el => {
      el.textContent = `$${depositDollars}`;
    });
  }
}

// Global initialization
if (typeof window !== 'undefined') {
  window.leafanooCartDrawer = null;
  const initCartDrawer = () => {
    window.leafanooCartDrawer = new CartDrawer();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCartDrawer);
  } else {
    initCartDrawer();
  }
}
