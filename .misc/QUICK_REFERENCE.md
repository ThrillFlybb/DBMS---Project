# Quick Reference Guide - DBMS Project

## 🚀 Quick Start

1. **Run the application**:
   ```bash
   start_with_tunnel.bat
   ```

2. **Access dashboard**: http://localhost:5000

3. **Navigate pages**:
   - Dashboard: Real-time metrics
   - Query Logs: View and search queries
   - Statistics: Query analytics
   - Performance: Baseline vs optimized comparison
   - Settings: Configure application

---

## 📁 File Purpose Summary

### Backend Files
- **`app.py`**: Main Flask application with all routes and logic
- **`requirements.txt`**: Python dependencies

### Data Files (`data/`)
- **`metrics.json`**: Real-time system metrics (QPS, latency, CPU, memory, storage)
- **`queries.json`**: Generated query logs (last 200 queries)
- **`benchmarks.json`**: Performance comparison data (baseline vs optimized)
- **`settings.json`**: User configuration
- **`recommendations.json`**: Optimization recommendations (future use)
- **`query_logs.json`**: Legacy query logs format

### Frontend Files (`templates/`)
- **`base.html`**: Common layout template
- **`dashboard.html`**: Main metrics dashboard
- **`queries.html`**: Query log viewer
- **`statistics.html`**: Query statistics and analytics
- **`performance.html`**: Performance comparison
- **`settings.html`**: Settings configuration page

### JavaScript Files (`static/js/`)
- **`app.js`**: Main frontend logic (dashboard, queries, performance, settings)
- **`performance.js`**: Legacy performance chart (unused)
- **`logs.js`**: Legacy logs loader (unused)

### CSS Files (`static/css/`)
- **`styles.css`**: Main stylesheet
- **`style.css`**: Legacy stylesheet

### Scripts
- **`start_with_tunnel.bat`**: Windows startup script with Cloudflared tunnel
- **`scripts/start.ps1`**: PowerShell startup script

---

## 🔑 Key Features

### 1. Real-time Metrics Dashboard
- **QPS**: Queries per second (80-240 range)
- **Latency**: Query execution time in ms (6-40ms)
- **CPU**: CPU usage percentage (5-98%)
- **Memory**: Memory usage percentage (5-98%)
- **Storage**: Database size in GB (starts at 221GB)

### 2. Query Log Viewer
- View all generated queries
- Search by SQL content
- Pagination (10, 20, 50 per page)
- Shows: Timestamp, Latency, Database, SQL

### 3. Performance Comparison
- Baseline vs optimized latency comparison
- CDF (Cumulative Distribution Function) chart
- Visual performance improvement

### 4. Statistics & Analytics
- Query type distribution (SELECT, INSERT, UPDATE, DELETE)
- Table usage frequency
- Hourly query distribution
- Query complexity analysis
- Summary statistics

### 5. Settings
- Database configuration
- Refresh interval
- Data source (JSON or REST)

---

## 🎯 API Endpoints

- **`GET /api/metrics`**: Get real-time metrics
- **`GET /api/queries?page=1&pageSize=20&search=`**: Get paginated queries
- **`GET /api/benchmarks`**: Get performance benchmarks
- **`GET /api/statistics`**: Get query statistics
- **`GET /api/settings`**: Get settings
- **`POST /api/settings`**: Save settings

---

## 🔄 How It Works

1. **Background Thread**: Runs every 1 second, generates metrics and queries
2. **State Management**: Maintains 60-point sliding window for metrics
3. **Query Generation**: Creates realistic SQL queries (SELECT, INSERT, UPDATE, DELETE)
4. **Data Storage**: Writes to JSON files for persistence
5. **Frontend Polling**: Polls API endpoints for updates
6. **Chart Updates**: Updates charts with new data points

---

## 📊 Database Tables Simulated

1. **users**: User information (id, name, email, age, status, created_at, is_premium)
2. **orders**: Order information (id, user_id, product_name, amount, status, order_date, quantity)
3. **payments**: Payment information (id, order_id, amount, payment_method, status, transaction_date)
4. **audit_logs**: Audit trail (id, user_id, action, table_name, created_at, ip_address)

---

## ⚙️ Configuration

### Default Settings:
- **Host**: localhost
- **Port**: 5432
- **User**: admin
- **Database**: app
- **Refresh Interval**: 5000ms (5 seconds)
- **Data Source**: json

### Change Settings:
1. Go to `/settings` page
2. Update desired settings
3. Click "Save"
4. Settings saved to `data/settings.json`

---

## 🐛 Troubleshooting

### Application won't start:
- Check Python is installed: `python --version`
- Check dependencies: `pip install -r requirements.txt`
- Check port 5000 is available

### Charts not updating:
- Check browser console for errors
- Verify API endpoints are working: http://localhost:5000/api/metrics
- Check refresh interval in settings

### No data showing:
- Wait a few seconds for simulator to generate data
- Check `data/` directory has JSON files
- Verify Flask app is running

---

## 📚 For More Details

See **PROJECT_DOCUMENTATION.md** for complete documentation.

