const ctx = document.getElementById('performanceChart');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Before Index', 'After Index'],
    datasets: [{
      label: 'Query Latency (ms)',
      data: [15.2, 8.7],
      borderColor: '#28a745',
      fill: false
    }]
  }
});
