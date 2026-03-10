/**
 * Loads shared header and footer components into all pages.
 *
 * Usage: Add these placeholders in your HTML:
 *   <div id="site-header"></div>   (where the header should go)
 *   <div id="site-footer"></div>   (where the footer should go)
 *
 * Then include this script:
 *   <script src="js/components.js"></script>
 */

(function () {
  function loadComponent(id, file, callback) {
    var el = document.getElementById(id);
    if (!el) return;

    fetch(file)
      .then(function (res) { return res.text(); })
      .then(function (html) {
        el.outerHTML = html;
        if (callback) callback();
      })
      .catch(function (err) {
        console.warn('Failed to load ' + file + ':', err);
      });
  }

  function highlightActiveNav() {
    var path = window.location.pathname.split('/').pop() || 'index.html';
    var links = document.querySelectorAll('.header-nav > a');
    links.forEach(function (link) {
      var href = link.getAttribute('href');
      if (href === path || (path === '' && href === 'index.html')) {
        link.classList.add('active');
      }
    });
  }

  function initMobileToggle() {
    var toggle = document.querySelector('.mobile-toggle');
    var nav = document.querySelector('.header-nav');
    if (toggle && nav) {
      toggle.addEventListener('click', function () {
        nav.classList.toggle('nav-open');
        toggle.classList.toggle('active');
      });
    }
  }

  // Load both components
  loadComponent('site-header', 'components/header.html', function () {
    highlightActiveNav();
    initMobileToggle();
  });

  loadComponent('site-footer', 'components/footer.html');
})();
