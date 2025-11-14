# Database Management System (DBMS) Project - Complete Documentation

## 📋 Project Overview

This is an **Automated Database Index Optimization Dashboard** built with Flask (Python backend) and a modern web frontend. The system simulates database query monitoring, performance metrics tracking, and provides real-time visualization of database performance metrics including QPS (Queries Per Second), latency, CPU, memory, and storage usage.

---

## 🎯 Main Purpose

The project serves as a **Database Performance Monitoring and Optimization Dashboard** that:
1. **Monitors** database query performance in real-time
2. **Simulates** realistic database queries across multiple tables
3. **Visualizes** performance metrics through interactive charts
4. **Tracks** query logs and statistics
5. **Compares** baseline vs optimized performance
6. **Provides** analytics on query patterns and usage

---

## 🏗️ Architecture Overview

### Technology Stack
- **Backend**: Flask (Python web framework)
- **Frontend**: HTML5, JavaScript (Vanilla), Chart.js for visualizations
- **Styling**: Pico CSS framework
- **Data Storage**: JSON files (simulated database)
- **Real-time Updates**: Threading-based simulator with 1-second intervals
- **Optional**: psutil for realistic system metrics

---

## 📁 File Structure & Detailed Explanation

### Root Directory Files

#### 1. **`app.py`** (559 lines) - Main Application Backend
**Purpose**: Core Flask application with all backend logic

**Key Components**:

##### a. **QueryGenerator Class** (Lines 41-296)
- **Purpose**: Generates realistic SQL queries for simulation
- **Why**: Creates diverse query patterns to simulate real-world database usage
- **Features**:
  - **Schema Definition**: Defines 4 tables with realistic column types:
    - `users`: id, name, email, age, status, created_at, is_premium
    - `orders`: id, user_id, product_name, amount, status, order_date, quantity
    - `payments`: id, order_id, amount, payment_method, status, transaction_date
    - `audit_logs`: id, user_id, action, table_name, created_at, ip_address
  - **Query Types Generated**:
    - SELECT queries (50% weight): Simple selects, WHERE clauses, JOINs, COUNT queries, ORDER BY, LIKE searches
    - INSERT queries (20% weight): Realistic data insertion
    - UPDATE queries (20% weight): Conditional updates
    - DELETE queries (5% weight): Conditional deletions
  - **Realistic Data Generation**:
    - Names, emails, product names, IP addresses
    - Date ranges, numeric ranges, enum values
    - Foreign key relationships maintained

##### b. **_RealtimeState Class** (Lines 302-372)
- **Purpose**: Maintains real-time state and simulates database metrics
- **Why**: Provides continuous data updates for dashboard visualization
- **Features**:
  - **Thread-safe** state management using locks
  - **Sliding window** of 60 data points for metrics
  - **Metrics Tracked**:
    - QPS (Queries Per Second): 80-240 range
    - Latency (ms): 6-40ms range, inversely correlated with QPS
    - CPU (%): 5-98%, uses psutil if available
    - Memory (%): 5-98%, uses psutil if available
    - Storage (GB): Gradually increasing from 221GB base
  - **Auto-generates** query logs every second
  - **Writes** to JSON files for persistence

##### c. **Flask Routes - Web Pages** (Lines 390-421)
- `/` - Redirects to dashboard
- `/dashboard` - Main metrics dashboard page
- `/queries` - Query log viewer page
- `/performance` - Performance comparison page
- `/settings` - Configuration settings page
- `/statistics` - Query statistics and analytics page

##### d. **API Endpoints** (Lines 424-546)
- **`GET /api/metrics`**: Returns real-time metrics (QPS, latency, CPU, memory, storage)
  - Supports both JSON file source and REST API source
  - Falls back to JSON if REST fails
- **`GET /api/queries`**: Returns paginated query logs
  - Parameters: `page`, `pageSize`, `search`
  - Supports search filtering by SQL content
- **`GET /api/benchmarks`**: Returns baseline vs optimized latency comparison
  - Baseline: Current latency + 8-9.5ms
  - Optimized: Current latency - 2-3ms
- **`GET /api/statistics`**: Returns query analytics
  - Query type distribution (SELECT, INSERT, UPDATE, DELETE)
  - Table usage frequency
  - Hourly query distribution
  - Query complexity analysis (simple, medium, complex)
- **`GET/POST /api/settings`**: Manages application settings
  - Database connection settings
  - Refresh intervals
  - Data source configuration (JSON or REST)

##### e. **Helper Functions**
- **`_read_json(filename, default)`**: Safely reads JSON files
- **`_write_json(filename, payload)`**: Safely writes JSON files
- **`_start_simulator_thread()`**: Starts background thread for real-time updates

#### 2. **`requirements.txt`** - Python Dependencies
**Purpose**: Lists all required Python packages

**Dependencies**:
- `Flask==3.0.0`: Web framework
- `psutil==6.0.0`: System and process utilities (optional, for realistic metrics)
- `waitress==3.0.0`: Production WSGI server
- `requests==2.32.3`: HTTP library for REST API integration

#### 3. **`start_with_tunnel.bat`** (90 lines) - Windows Startup Script
**Purpose**: Automated startup script for Windows that sets up environment and creates public tunnel

**Features**:
- Creates virtual environment if missing
- Installs dependencies
- Starts Flask app in separate window
- Opens browser automatically
- Creates Cloudflared tunnel for public access
- Error handling and user-friendly messages

---

### Data Directory (`data/`)

#### 1. **`benchmarks.json`** - Performance Benchmarks
**Purpose**: Stores baseline vs optimized latency comparisons
**Structure**:
```json
{
  "baseline": {"latencyMs": [array of latency values]},
  "optimized": {"latencyMs": [array of latency values]}
}
```
**Why**: Used for performance comparison visualization

#### 2. **`metrics.json`** - Real-time Metrics
**Purpose**: Stores current system metrics
**Structure**:
```json
{
  "timestamp": "ISO timestamp",
  "series": {
    "labels": [time labels],
    "qps": [QPS values],
    "latencyMs": [latency values],
    "cpu": [CPU percentages],
    "memory": [memory percentages],
    "storageGb": [storage values]
  }
}
```
**Why**: Provides data for dashboard charts (60-point sliding window)

#### 3. **`queries.json`** - Query Logs
**Purpose**: Stores generated query logs
**Structure**:
```json
{
  "items": [
    {
      "timestamp": "ISO timestamp",
      "latencyMs": number,
      "database": "app|analytics|payments",
      "sql": "SQL query string",
      "type": "SELECT|INSERT|UPDATE|DELETE",
      "table": "table name"
    }
  ]
}
```
**Why**: Used for query log viewer and statistics (stores last 200 queries)

#### 4. **`query_logs.json`** - Legacy Query Logs (Optional)
**Purpose**: Alternative format for query logs (legacy)
**Structure**: Array of query objects
**Why**: May be used by other components or for migration

#### 5. **`recommendations.json`** - Optimization Recommendations
**Purpose**: Stores index optimization recommendations (if implemented)
**Why**: Would contain suggested indexes based on query patterns

#### 6. **`settings.json`** - Application Settings
**Purpose**: Stores user configuration
**Structure**:
```json
{
  "db": {
    "host": "localhost",
    "port": 5432,
    "user": "admin",
    "database": "app"
  },
  "refreshIntervalMs": 5000,
  "dataSource": "json|rest",
  "backendBaseUrl": "optional REST API URL"
}
```
**Why**: Persists user settings between sessions

---

### Templates Directory (`templates/`)

#### 1. **`base.html`** - Base Template
**Purpose**: Common layout for all pages
**Features**:
- Navigation bar with links to all pages
- Chart.js library inclusion
- Pico CSS framework
- Common JavaScript file (`app.js`)
- Responsive design

**Navigation Links**:
- Dashboard
- Query Logs
- Statistics
- Performance
- Settings

#### 2. **`dashboard.html`** - Main Dashboard Page
**Purpose**: Real-time metrics visualization
**Features**:
- 5 real-time charts:
  1. **QPS Chart**: Queries per second over time
  2. **Latency Chart**: Query latency in milliseconds
  3. **CPU Chart**: CPU usage percentage
  4. **Memory Chart**: Memory usage percentage
  5. **Storage Chart**: Storage usage in GB
- Auto-refreshes based on settings (default 5 seconds)
- Streaming updates (appends new data points)
- 60-point sliding window

#### 3. **`queries.html`** - Query Log Viewer
**Purpose**: View and search query logs
**Features**:
- Searchable query table
- Pagination (10, 20, 50 items per page)
- Displays: Timestamp, Latency, Database, SQL query
- Real-time query log updates
- SQL syntax highlighting (via `<code>` tags)

#### 4. **`performance.html`** - Performance Comparison Page
**Purpose**: Compare baseline vs optimized performance
**Features**:
- **Latency Comparison Chart**: Line chart showing baseline vs optimized latency
- **CDF Chart**: Cumulative Distribution Function showing latency distribution
- Updates every 1 second
- Visualizes performance improvement from optimization

#### 5. **`statistics.html`** - Query Statistics Page
**Purpose**: Advanced analytics on query patterns
**Features**:
- **Query Type Distribution**: Doughnut chart (SELECT, INSERT, UPDATE, DELETE)
- **Table Usage Frequency**: Bar chart showing most accessed tables
- **Hourly Distribution**: Line chart showing queries per hour
- **Query Complexity Analysis**: Polar area chart (Simple, Medium, Complex)
- **Summary Statistics**:
  - Total queries
  - Most used query type
  - Most accessed table
  - Peak hour
- Auto-refreshes every 30 seconds
- Manual refresh button

#### 6. **`settings.html`** - Settings Page
**Purpose**: Configure application settings
**Features**:
- **Database Settings**:
  - Host, Port, User, Database name
- **Frontend Settings**:
  - Refresh interval (milliseconds)
  - Data source (JSON or REST API)
  - Backend base URL (for REST mode)
- Save functionality with confirmation
- Settings persist to `settings.json`

---

### Static Directory (`static/`)

#### JavaScript Files (`static/js/`)

##### 1. **`app.js`** (209 lines) - Main Frontend Application
**Purpose**: Core JavaScript logic for all pages

**Key Functions**:

- **`initDashboard()`** (Lines 38-87):
  - Initializes 5 real-time charts
  - Fetches metrics every N milliseconds (configurable)
  - Updates charts with streaming data
  - Maintains 60-point sliding window
  - Uses Chart.js for visualization
  - Gradient fills for aesthetic appeal

- **`initQueries()`** (Lines 89-120):
  - Loads query logs with pagination
  - Implements search functionality
  - Updates table with query data
  - Handles pagination clicks
  - Formats SQL queries for display

- **`initPerformance()`** (Lines 122-181):
  - Creates latency comparison chart
  - Creates CDF (Cumulative Distribution Function) chart
  - Calculates CDF from latency data
  - Updates every 1 second
  - Shows performance improvement visualization

- **`initSettings()`** (Lines 183-203):
  - Handles settings form submission
  - Saves settings to backend
  - Shows save confirmation
  - Updates form with current settings

**Helper Functions**:
- **`fetchJson(url, options)`**: Wrapper for fetch API
- **`lineChart(ctx, label, data, color)`**: Creates Chart.js line chart with gradient

##### 2. **`performance.js`** (14 lines) - Legacy Performance Chart
**Purpose**: Simple performance chart (may be legacy/unused)
**Features**: Basic line chart showing before/after index performance

##### 3. **`logs.js`** (12 lines) - Legacy Logs Loader
**Purpose**: Legacy query logs loader (may be unused)
**Features**: Fetches and displays logs from `/api/logs` endpoint

#### CSS Files (`static/css/`)

##### 1. **`styles.css`** (18 lines) - Main Stylesheet
**Purpose**: Custom styles for the application
**Features**:
- Chart grid layout (2 columns)
- Responsive design
- Chart sizing and spacing
- Pagination styling
- Code formatting for SQL queries

##### 2. **`style.css`** (32 lines) - Legacy Stylesheet
**Purpose**: Alternative stylesheet (may be legacy)
**Features**: Basic card-based layout, table styling

---

### Scripts Directory (`scripts/`)

#### 1. **`start.ps1`** - PowerShell Startup Script
**Purpose**: PowerShell version of startup script
**Features**:
- Creates virtual environment
- Installs dependencies
- Configures environment variables
- Starts Flask server
- Uses Waitress for production server

---

## 🔄 Data Flow & Real-time Updates

### How Real-time Updates Work:

1. **Background Thread** (`_start_simulator_thread()`):
   - Runs continuously in a daemon thread
   - Executes `STATE.tick()` every 1 second
   - Updates metrics, generates queries, writes to JSON files

2. **State Update Process** (`STATE.tick()`):
   - Calculates new metric values (QPS, latency, CPU, memory, storage)
   - Generates a new query using `QueryGenerator`
   - Appends query to queries list (max 200)
   - Writes updated data to JSON files
   - Maintains 60-point sliding window for metrics

3. **Frontend Polling**:
   - Dashboard polls `/api/metrics` every N seconds (default 5000ms)
   - Queries page loads data on page load and search
   - Performance page polls `/api/benchmarks` every 1 second
   - Statistics page polls `/api/statistics` every 30 seconds

4. **Chart Updates**:
   - New data points appended to charts
   - Old data points removed (sliding window)
   - Smooth animations for better UX
   - Charts update in "active" mode for performance

---

## 🎨 User Interface Features

### Dashboard Page:
- **Real-time Metrics**: 5 live-updating charts
- **Visual Appeal**: Gradient fills, smooth animations
- **Responsive**: Works on different screen sizes
- **Auto-refresh**: Configurable refresh interval

### Query Logs Page:
- **Search**: Filter queries by SQL content
- **Pagination**: Navigate through large query sets
- **Sortable**: View by timestamp, latency, database
- **Readable**: SQL queries formatted with syntax highlighting

### Performance Page:
- **Comparison**: Baseline vs optimized latency
- **Statistical Analysis**: CDF chart for distribution
- **Visual Feedback**: Clear performance improvement visualization

### Statistics Page:
- **Multiple Charts**: 4 different chart types
- **Summary Cards**: Key metrics at a glance
- **Detailed Analytics**: Query patterns, table usage, hourly trends
- **Auto-refresh**: Keeps data current

### Settings Page:
- **Easy Configuration**: Simple form-based interface
- **Persistent**: Settings saved to JSON file
- **Flexible**: Support for JSON and REST data sources

---

## 🔧 Configuration & Settings

### Available Settings:

1. **Database Configuration**:
   - Host: Database server hostname
   - Port: Database server port (default: 5432)
   - User: Database username
   - Database: Database name

2. **Frontend Configuration**:
   - Refresh Interval: Milliseconds between updates (default: 5000)
   - Data Source: "json" or "rest"
   - Backend Base URL: REST API endpoint (if using REST mode)

### How to Configure:

1. Navigate to `/settings` page
2. Update desired settings
3. Click "Save" button
4. Settings are persisted to `data/settings.json`
5. Changes take effect immediately for refresh interval
6. Data source changes require page refresh

---

## 🚀 Running the Application

### Method 1: Using Batch Script (Windows)
```bash
start_with_tunnel.bat
```
- Automatically sets up environment
- Creates public tunnel via Cloudflared
- Opens browser automatically

### Method 2: Using PowerShell Script
```powershell
.\scripts\start.ps1
```
- Sets up virtual environment
- Installs dependencies
- Starts Flask server

### Method 3: Manual Start
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set environment variables
set PORT=5000
set USE_WAITRESS=1

# Run application
python app.py
```

### Accessing the Application:
- **Local**: http://localhost:5000
- **Public** (with tunnel): URL provided by Cloudflared

---

## 📊 Metrics Explanation

### QPS (Queries Per Second):
- **What**: Number of database queries executed per second
- **Range**: 80-240 queries/second
- **Why Important**: Indicates database load
- **Visualization**: Line chart with blue gradient

### Latency (ms):
- **What**: Time taken to execute a query in milliseconds
- **Range**: 6-40ms (inversely correlated with QPS)
- **Why Important**: Measures query performance
- **Visualization**: Line chart with green gradient

### CPU (%):
- **What**: CPU usage percentage
- **Range**: 5-98%
- **Why Important**: Indicates system resource usage
- **Visualization**: Line chart with orange gradient
- **Note**: Uses psutil if available, otherwise simulated

### Memory (%):
- **What**: Memory usage percentage
- **Range**: 5-98%
- **Why Important**: Tracks memory consumption
- **Visualization**: Line chart with purple gradient
- **Note**: Uses psutil if available, otherwise simulated

### Storage (GB):
- **What**: Database storage size in gigabytes
- **Range**: Starts at 221GB, gradually increases
- **Why Important**: Monitors database growth
- **Visualization**: Line chart with cyan gradient

---

## 🔍 Query Generation Details

### Query Types:

1. **SELECT Queries** (50% probability):
   - Simple SELECT: `SELECT * FROM table LIMIT n`
   - WHERE LIKE: `SELECT * FROM table WHERE column LIKE '%pattern%'`
   - WHERE Range: `SELECT * FROM table WHERE column BETWEEN x AND y`
   - WHERE Enum: `SELECT * FROM table WHERE status = 'value'`
   - COUNT: `SELECT COUNT(*) FROM table WHERE condition`
   - JOIN: `SELECT * FROM table1 JOIN table2 ON condition`
   - ORDER BY: `SELECT * FROM table ORDER BY column DESC LIMIT n`

2. **INSERT Queries** (20% probability):
   - Generates realistic data for all columns
   - Skips primary keys (auto-generated)
   - Maintains foreign key relationships

3. **UPDATE Queries** (20% probability):
   - Updates non-primary key columns
   - Uses WHERE clause with conditions
   - Generates realistic new values

4. **DELETE Queries** (5% probability):
   - Deletes based on conditions
   - Uses WHERE clause
   - Maintains referential integrity patterns

### Table Relationships:
- `orders.user_id` → `users.id`
- `payments.order_id` → `orders.id`
- `audit_logs.user_id` → `users.id`

---

## 🎯 Use Cases

### 1. Database Performance Monitoring:
- Monitor real-time query performance
- Track system resource usage
- Identify performance bottlenecks

### 2. Query Analysis:
- Analyze query patterns
- Identify most used tables
- Understand query complexity
- Track query distribution over time

### 3. Performance Optimization:
- Compare baseline vs optimized performance
- Visualize optimization improvements
- Track latency improvements

### 4. Database Administration:
- View query logs
- Search for specific queries
- Monitor database growth
- Track system health

---

## 🔐 Security Considerations

### Current Implementation:
- **No Authentication**: Application is open to anyone
- **Local by Default**: Runs on localhost
- **Public Access**: Cloudflared tunnel provides public access (use with caution)
- **No Input Validation**: SQL queries are simulated, not executed

### Recommendations for Production:
1. Add authentication/authorization
2. Implement rate limiting
3. Add input validation
4. Use HTTPS
5. Implement proper error handling
6. Add logging and monitoring
7. Secure database connections

---

## 🐛 Known Limitations

1. **Simulated Data**: All data is generated, not from real database
2. **No Real Database Connection**: Uses JSON files for data storage
3. **No Authentication**: No user authentication system
4. **Limited Error Handling**: Basic error handling implemented
5. **No Data Persistence**: Data resets on application restart (except settings)
6. **Single Thread**: Simulator runs in single thread (sufficient for simulation)

---

## 🔮 Future Enhancements

### Potential Improvements:
1. **Real Database Integration**: Connect to actual database
2. **Index Recommendations**: Automatic index suggestions based on queries
3. **Query Optimization**: Automatic query optimization suggestions
4. **Alerting**: Alerts for performance issues
5. **Historical Data**: Long-term data storage and analysis
6. **Export Functionality**: Export reports and data
7. **User Authentication**: Multi-user support with roles
8. **API Documentation**: Swagger/OpenAPI documentation
9. **Unit Tests**: Comprehensive test coverage
10. **Docker Support**: Containerization for easy deployment

---

## 📝 Summary

This project is a **comprehensive database performance monitoring dashboard** that:
- Simulates realistic database queries
- Tracks real-time performance metrics
- Provides beautiful visualizations
- Offers detailed analytics
- Supports configuration and customization
- Runs on Flask with modern web technologies

The system is designed for **educational purposes** and **demonstration** of database monitoring concepts, with the ability to be extended for production use with real database connections and additional features.

---

## 🏁 Conclusion

This DBMS project provides a complete solution for database performance monitoring with:
- ✅ Real-time metrics tracking
- ✅ Query log viewing and analysis
- ✅ Performance comparison
- ✅ Statistical analytics
- ✅ Configurable settings
- ✅ Beautiful, responsive UI
- ✅ Extensible architecture

The codebase is well-structured, documented, and ready for further development and enhancement.

