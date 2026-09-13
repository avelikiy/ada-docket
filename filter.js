// Client-side filter over the record table, on pages that have one.
(function () {
  var q = document.getElementById('q');
  var out = document.getElementById('count');
  if (!q) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll('#rows tr'));
  function apply() {
    var term = q.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {
      var hit = !term || row.dataset.search.indexOf(term) !== -1;
      row.hidden = !hit;
      if (hit) shown++;
    });
    out.textContent = term ? shown + ' of ' + rows.length + ' shown' : '';
  }
  q.addEventListener('input', apply);
  apply();
})();
