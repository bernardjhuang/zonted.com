// Trading dropdown in the site nav: <details> handles the toggle natively;
// this only adds close-on-outside-click and Escape, which <details> lacks.
(function () {
  function closeAll(except) {
    document.querySelectorAll('details.zn-dd[open]').forEach(function (d) {
      if (d !== except) d.removeAttribute('open');
    });
  }
  document.addEventListener('click', function (e) {
    var inside = e.target.closest ? e.target.closest('details.zn-dd') : null;
    closeAll(inside);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeAll(null);
  });
})();
