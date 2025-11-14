window.IndexUI = (function () {
	const api = {
		metrics: '/api/metrics',
		queries: '/api/queries',
		settings: '/api/settings'
	};

	async function fetchJson(url, options) {
		const res = await fetch(url, options);
		return await res.json();
	}

    function lineChart(ctx, label, data, color) {
        const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
        gradient.addColorStop(0, color + '33'); // ~20% alpha
        gradient.addColorStop(1, color + '00'); // transparent
        return new Chart(ctx, {
			type: 'line',
			data: {
				labels: data.labels,
                datasets: [{ label, data: data.values, borderColor: color, backgroundColor: gradient, fill: true, pointRadius: 0, borderWidth: 2 }]
			},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 800, easing: 'easeInOutSine' },
                interaction: { intersect: false, mode: 'index' },
                elements: { line: { tension: 0.25 } },
                scales: {
                    x: { display: true, grid: { display: false } },
                    y: { display: true, grid: { color: 'rgba(0,0,0,0.08)' } }
                }
            }
		});
	}

	async function initDashboard() {
        const settings = await fetchJson(api.settings);
        const interval = Math.max(1000, settings.refreshIntervalMs || 5000);
		const charts = {};
        const maxPoints = 60;
        async function render() {
			const data = await fetchJson(api.metrics);
			const s = data.series || {};
            const labels = s.labels || Array.from({ length: Math.max(
				(s.qps || []).length,
				(s.latencyMs || []).length,
				(s.cpu || []).length,
				(s.memory || []).length,
				(s.storageGb || []).length
			)}, (_, i) => i + 1);

			const defs = [
				{ id: 'qpsChart', label: 'QPS', values: s.qps || [], color: '#2563eb' },
				{ id: 'latencyChart', label: 'Latency (ms)', values: s.latencyMs || [], color: '#16a34a' },
				{ id: 'cpuChart', label: 'CPU (%)', values: s.cpu || [], color: '#ea580c' },
				{ id: 'memoryChart', label: 'Memory (%)', values: s.memory || [], color: '#7c3aed' },
				{ id: 'storageChart', label: 'Storage (GB)', values: s.storageGb || [], color: '#0ea5e9' }
			];
			for (const d of defs) {
				const ctx = document.getElementById(d.id);
				if (!ctx) continue;
				const ctx2d = ctx.getContext('2d');
				const payload = { labels, values: d.values };
                if (!charts[d.id]) {
                    charts[d.id] = lineChart(ctx2d, d.label, payload, d.color);
                } else {
                    // Stream-like update: append last point, enforce sliding window
                    const ch = charts[d.id];
                    const newLabel = labels[labels.length - 1];
                    const newVal = d.values[d.values.length - 1];
                    if (newLabel !== undefined && newVal !== undefined) {
                        ch.data.labels.push(newLabel);
                        ch.data.datasets[0].data.push(newVal);
                        if (ch.data.labels.length > maxPoints) {
                            ch.data.labels.shift();
                            ch.data.datasets[0].data.shift();
                        }
                    }
                    ch.update('active');
                }
			}
		}
		render();
		setInterval(render, interval);
	}

	async function initQueries() {
		const tbody = document.getElementById('queriesTbody');
		const form = document.getElementById('querySearchForm');
		const pagination = document.getElementById('pagination');
		let page = 1;
		async function load() {
			const search = document.getElementById('querySearch').value;
			const pageSize = document.getElementById('pageSize').value;
			const data = await fetchJson(`${api.queries}?page=${page}&pageSize=${pageSize}&search=${encodeURIComponent(search)}`);
			tbody.innerHTML = data.items.map(q => `
				<tr>
					<td>${q.timestamp}</td>
					<td>${q.latencyMs}</td>
					<td>${q.database}</td>
					<td><code style="white-space: pre-line">${q.sql}</code></td>
				</tr>
			`).join('');
			const pages = Math.max(1, Math.ceil(data.total / data.pageSize));
			pagination.innerHTML = Array.from({ length: pages }, (_, i) => i + 1).map(i => `
				<li><a href="#" data-page="${i}" ${i===data.page?'class="primary"':''}>${i}</a></li>
			`).join('');
		}
		pagination.addEventListener('click', (e) => {
			const a = e.target.closest('a[data-page]');
			if (!a) return;
			e.preventDefault();
			page = parseInt(a.getAttribute('data-page'));
			load();
		});
		form.addEventListener('submit', (e) => { e.preventDefault(); page = 1; load(); });
		load();
		// Auto-refresh every 5 seconds
		setInterval(load, 5000);
	}


	async function initSettings() {
		const form = document.getElementById('settingsForm');
		const status = document.getElementById('settingsStatus');
		form.addEventListener('submit', async (e) => {
			e.preventDefault();
			const payload = {
				db: {
					host: document.getElementById('dbHost').value,
					port: parseInt(document.getElementById('dbPort').value),
					user: document.getElementById('dbUser').value,
					database: document.getElementById('dbName').value
				},
				refreshIntervalMs: parseInt(document.getElementById('refreshInterval').value),
				dataSource: document.getElementById('dataSource').value,
				backendBaseUrl: document.getElementById('backendBaseUrl') ? document.getElementById('backendBaseUrl').value : ''
			};
			await fetchJson(api.settings, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
			status.textContent = 'Saved';
			setTimeout(()=> status.textContent = '', 1500);
		});
	}

	return { initDashboard, initQueries, initSettings };
})();


