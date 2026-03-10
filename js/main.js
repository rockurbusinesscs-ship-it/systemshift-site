/* ══════════════════════════════════════════════════════════════
   SYSTEMSHIFT HQ — SHARED JS
   ══════════════════════════════════════════════════════════════ */

// Header scroll effect
(function() {
  var header = document.querySelector('.site-header');
  if (!header) return;
  window.addEventListener('scroll', function() {
    header.classList.toggle('scrolled', window.scrollY > 40);
  });
})();

// Mobile menu toggle
(function() {
  var toggle = document.querySelector('.mobile-toggle');
  var nav = document.querySelector('.header-nav');
  if (!toggle || !nav) return;

  toggle.addEventListener('click', function() {
    toggle.classList.toggle('open');
    nav.classList.toggle('open');
  });

  // Close on link click
  nav.querySelectorAll('a').forEach(function(link) {
    link.addEventListener('click', function() {
      toggle.classList.remove('open');
      nav.classList.remove('open');
    });
  });
})();

// FAQ accordion
(function() {
  document.querySelectorAll('.faq-question').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var item = btn.closest('.faq-item');
      var wasOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach(function(i) { i.classList.remove('open'); });
      if (!wasOpen) item.classList.add('open');
    });
  });
})();

// Scroll fade-in animations
(function() {
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.fade-up').forEach(function(el) {
    observer.observe(el);
  });
})();

// Stat counter animation
(function() {
  var animated = false;
  var statsSection = document.querySelector('.stats-grid');
  if (!statsSection) return;

  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting && !animated) {
        animated = true;
        document.querySelectorAll('.stat-number').forEach(function(el) {
          var text = el.textContent;
          var match = text.match(/([\d,]+)/);
          if (!match) return;
          var target = parseInt(match[1].replace(/,/g, ''));
          if (target > 10000) return;
          var current = 0;
          var step = Math.ceil(target / 40);
          var suffix = text.replace(match[1], '').trim();
          var prefix = text.indexOf(match[1]) > 0 ? text.substring(0, text.indexOf(match[1])) : '';
          var timer = setInterval(function() {
            current = Math.min(current + step, target);
            el.textContent = prefix + current.toLocaleString() + suffix;
            if (current >= target) clearInterval(timer);
          }, 30);
        });
        observer.disconnect();
      }
    });
  }, { threshold: 0.3 });

  observer.observe(statsSection);
})();

// Active nav link
(function() {
  var path = window.location.pathname;
  document.querySelectorAll('.header-nav a').forEach(function(link) {
    var href = link.getAttribute('href');
    if (href === path || (href !== '/' && path.startsWith(href))) {
      link.classList.add('active');
    }
    if (path === '/' && (href === '/' || href === '/index.html' || href === 'index.html')) {
      link.classList.add('active');
    }
  });
})();
