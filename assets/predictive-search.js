/**
 * Leafanoo Predictive Search JavaScript
 */

class PredictiveSearch {
  constructor() {
    this.inputs = document.querySelectorAll('input[type="search"][data-predictive-search]');
    this.bindEvents();
  }

  bindEvents() {
    this.inputs.forEach(input => {
      let timeout = null;
      input.addEventListener('input', (e) => {
        clearTimeout(timeout);
        const query = e.target.value.trim();
        if (query.length < 2) {
          this.closeResults(input);
          return;
        }

        timeout = setTimeout(() => {
          this.fetchResults(query, input);
        }, 300);
      });

      input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.closeResults(input);
      });
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('.predictive-search-wrapper')) {
        document.querySelectorAll('.predictive-search-results').forEach(el => el.style.display = 'none');
      }
    });
  }

  async fetchResults(query, input) {
    try {
      const res = await fetch(`/search/suggest.json?q=${encodeURIComponent(query)}&resources[type]=product,collection&resources[limit]=6`);
      const data = await res.json();
      this.renderResults(data.resources.results, input);
    } catch (e) {
      console.error('Predictive search fetch error:', e);
    }
  }

  renderResults(results, input) {
    let container = input.parentElement.querySelector('.predictive-search-results');
    if (!container) {
      container = document.createElement('div');
      container.className = 'predictive-search-results';
      container.style.cssText = 'position: absolute; top: 100%; left: 0; right: 0; background: #fff; border: 1px solid #E8E8E0; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); z-index: 1000; max-height: 400px; overflow-y: auto; margin-top: 4px; padding: 0.5rem 0;';
      input.parentElement.style.position = 'relative';
      input.parentElement.appendChild(container);
    }

    const products = results.products || [];
    if (products.length === 0) {
      container.innerHTML = '<div style="padding: 1rem; text-align: center; color: #777; font-size: 0.9rem;">No products found</div>';
    } else {
      container.innerHTML = `
        <div style="padding: 0.5rem 1rem; font-size: 0.75rem; text-transform: uppercase; color: #888; font-weight: 600;">Products</div>
        ${products.map(p => `
          <a href="${p.url}" style="display: flex; gap: 0.75rem; align-items: center; padding: 0.5rem 1rem; text-decoration: none; color: inherit; transition: background 0.15s;" onmouseover="this.style.background='#F5F7F5'" onmouseout="this.style.background='transparent'">
            <img src="${p.image}" alt="${p.title}" style="width: 44px; height: 44px; object-fit: contain; border-radius: 4px; background: #F8F8F8;">
            <div>
              <div style="font-size: 0.9rem; font-weight: 500; color: #1A1A1A;">${p.title}</div>
              <div style="font-size: 0.85rem; color: #2D6A4F; font-weight: 600;">$${p.price}</div>
            </div>
          </a>
        `).join('')}
      `;
    }
    container.style.display = 'block';
  }

  closeResults(input) {
    const container = input.parentElement.querySelector('.predictive-search-results');
    if (container) container.style.display = 'none';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new PredictiveSearch();
});
