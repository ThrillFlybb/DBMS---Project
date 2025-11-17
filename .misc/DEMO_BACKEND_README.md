# Demo Backend Server - REST API Demonstration

This is a standalone demo backend server that demonstrates how to use the REST data source feature in the DBMS project.

## 🚀 Quick Start

### 1. Install Dependencies

Make sure you have `flask-cors` installed:

```bash
pip install flask-cors
```

Or add it to your requirements.txt:
```
flask-cors
```

### 2. Start the Demo Backend Server

```bash
python demo_backend.py
```

The server will start on **http://localhost:5001**

### 3. Configure the Main Application

1. Start your main Flask application (`app.py`) on port 5000
2. Open the application in your browser: http://localhost:5000
3. Navigate to **Settings** page
4. Change **Data Source** from "JSON" to **"REST"**
5. Set **Backend Base URL** to: `http://localhost:5001`
6. Click **Save Settings**

### 4. Test the Integration

Once configured, the main application will fetch data from the demo backend server instead of local JSON files. You can verify this by:

- Checking the **Dashboard** - metrics should load from backend
- Checking **Query Logs** - queries should load from backend
- Checking **Statistics** - statistics should load from backend

## 📡 API Endpoints

The demo backend provides these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/metrics` | GET | Real-time metrics (QPS, latency, CPU, memory, storage) |
| `/queries` | GET | Paginated query logs with search support |
| `/statistics` | GET | Query statistics (types, table usage, column frequency, indexes) |
| `/benchmarks` | GET | Performance benchmarks (for compatibility) |

### Query Parameters

**`/queries` endpoint supports:**
- `page` - Page number (default: 1)
- `pageSize` - Items per page (default: 20)
- `search` - Search term to filter SQL queries

**Example:**
```
GET http://localhost:5001/queries?page=1&pageSize=20&search=SELECT
```

## 🔧 How It Works

1. **Main Application** (`app.py`) runs on port 5000
2. **Demo Backend** (`demo_backend.py`) runs on port 5001
3. When Data Source is set to "REST", the main app makes HTTP requests to the backend
4. The backend reads from the same data files (`query_log.txt`, `auto_index.db`, etc.)
5. Data is returned as JSON responses

## 🎯 Use Cases

This demo backend is useful for:

- **Testing REST API integration** - Verify that the frontend correctly calls REST endpoints
- **Simulating remote backend** - Test how the app behaves with a separate backend server
- **Development** - Develop backend features independently
- **Production simulation** - Test production-like scenarios with separate services

## 🔄 Switching Back

To switch back to JSON data source:

1. Go to **Settings** page
2. Change **Data Source** back to **"JSON"**
3. Click **Save Settings**

The application will immediately switch back to reading from local JSON files.

## 📝 Notes

- The demo backend reads from the same data files as the main app
- Both servers can run simultaneously
- CORS is enabled to allow cross-origin requests
- The backend uses the same database and log files for consistency

## 🐛 Troubleshooting

**Backend not responding:**
- Check if port 5001 is available
- Verify flask-cors is installed
- Check console for error messages

**Data not loading:**
- Verify backend URL is correct in settings
- Check browser console for CORS errors
- Ensure both servers are running

**Connection refused:**
- Make sure demo_backend.py is running
- Check firewall settings
- Verify the port number matches

