/**
 * Leafanoo Cart Drawer JavaScript
 */

class CartDrawer {
  constructor() {
    this.drawer = document.getElementById('CartDrawer');
    if (!this.drawer) return;

    this.container = this.drawer.querySelector('.cart-drawer__container');
    this.backdrop = this.drawer.querySelector('.cart-drawer__backdrop');
    this.closeBtn = this.drawer.querySelector('.cart-drawer-close');
    this.itemsContainer = document.getElementById('CartDrawerItems');

    this.bindEvents();
  }

  bindEvents() {
    document.addEventListener('click', (e) => {
      const trigger = e.target.closest('[data-cart-drawer-trigger]');
      if (trigger) {
        e.preventDefault();
        this.open();
      }
    });

    document.addEventListener('cart:item-added', () => {
      this.refresh().then(() => this.open());
    });

    if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.close());
    if (this.backdrop) this.backdrop.addEventListener('click', () => this.close());

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen()) this.close();
    });
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

  async refresh() {
    try {
      const res = await fetch('/cart.js');
      const cart = await res.json();
      this.updateCounts(cart.item_count);
      this.updateSubtotal(cart.total_price);
      // Reload cart section
      const sectionRes = await fetch('/?section_id=cart-drawer');
      const text = await sectionRes.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(text, 'text/html');
      const newItems = doc.getElementById('CartDrawerItems');
      if (newItems && this.itemsContainer) {
        this.itemsContainer.innerHTML = newItems.innerHTML;
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
    const formatted = `$${(total / 100).toFixed(2)}`;
    document.querySelectorAll('.cart-drawer-subtotal').forEach(el => {
      el.textContent = formatted;
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.leafanooCartDrawer = new CartDrawer();
});
