async function loadLogs() {
  const res = await fetch('/api/logs');
  const logs = await res.json();
  const body = document.querySelector('#logsTable tbody');
  body.innerHTML = '';
  logs.forEach(l => {
    const row = `<tr><td>${l.query}</td><td>${l.time_ms}</td><td>${l.timestamp}</td></tr>`;
    body.innerHTML += row;
  });
}
loadLogs();
