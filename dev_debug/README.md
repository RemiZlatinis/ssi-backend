# SSI Debug Dashboard

A development-only debugging interface for the SSI (Service Status Indicator) backend that provides real-time monitoring of agents and services.

## 🚀 Features

### Three-Section Agent Detail View

1. **Agent Details & Services** (HTTP Polling - 1 second)
   - Live agent status information
   - Service list with real-time status updates
   - Pause/resume polling controls
   - Clear data options

2. **Agent Events Log** (WebSocket)
   - Live events from agent connections
   - Real-time message streaming
   - Auto-scrolling with event history
   - Color-coded event types

3. **Client Events Log** (WebSocket)  
   - Live events broadcast to clients
   - Real-time notification monitoring
   - Session-based event storage
   - Interactive controls

### Agent List View

- Overview of all agents with status indicators
- Live updates every second
- Filter and search capabilities
- Direct navigation to agent details

## 🔧 Installation & Setup

The debug dashboard is automatically enabled when `DEBUG=True`. No additional configuration required.

### Access Requirements

1. **Development Mode**: Must be running with `DEBUG=True`
2. **Authentication**: Requires valid Django user account
3. **Permissions**: Users can only debug their own agents (staff can see all)

### URL Structure

- **Dashboard Home**: `/dev-debug/` - Agent list overview
- **Agent Detail**: `/dev-debug/agent/<uuid>/` - Detailed agent view
- **WebSocket**: `/dev-debug/ws/agent/<uuid>/` - Real-time events
- **API**: `/dev-debug/api/agents/` and `/dev-debug/api/agent/<uuid>/` - Polling endpoints

## 🖥️ Usage

### Starting the Dashboard

1. Ensure you're running in development mode:
   ```bash
   DEBUG=true poetry run python manage.py runserver
   ```

2. Visit the dashboard:
   ```
   http://127.0.0.1:8000/dev-debug/
   ```

3. Log in with your Django credentials

### Monitoring Agents

1. **Agent List**: See all agents with live status
2. **Click Agent Name**: Navigate to detailed view
3. **Three Panel View**: Monitor status, agent events, and client events simultaneously

### Controls

- **Pause/Resume**: Control polling and event streaming
- **Clear**: Reset event logs or service lists
- **Auto-scroll**: Events automatically scroll to show newest entries

## 🏗️ Architecture

### Data Flow

```
Agent WebSocket Events
        ↓
AgentConsumer (same channel group)
        ↓
DebugDashboardConsumer (direct listener)
        ↓
    Frontend WebSocket
        ↓
    Event Logs Display

Client Broadcast Events
        ↓
Core Broadcasting Functions
        ↓
Client Group
        ↓
DebugDashboardConsumer (listener)
        ↓
    Frontend WebSocket
        ↓
    Client Event Logs Display
```

### Polling vs WebSocket

- **Agent/Service Status**: HTTP polling every 1 second
- **Agent Events**: WebSocket listening to agent channels
- **Client Events**: WebSocket listening to broadcast channels

### Security

- Only available in `DEBUG=True` environments
- Requires user authentication
- User isolation (can only access own agents)
- Staff privilege override

## 📱 Features

### Real-time Updates

- **Status Indicators**: Visual online/offline status
- **Live Counters**: Event counters per section
- **Connection Status**: WebSocket connection indicator
- **Timestamp Display**: Precise timing for all events

### Interactive Controls

- **Polling Control**: Pause/resume status updates
- **Event Control**: Pause/resume event streaming
- **Data Management**: Clear logs and refresh data
- **Navigation**: Easy access between agent views

### Responsive Design

- **Modern CSS**: Flexbox/Grid layouts
- **Mobile Friendly**: Responsive breakpoints
- **Dark Theme**: Developer-friendly dark interface throughout
- **Terminal-Style Event Logs**: Classic dark terminal aesthetic
- **High Contrast**: Optimized for long debugging sessions
- **Status Colors**: Consistent visual feedback on dark backgrounds

## 🛠️ Development

### File Structure

```
dev_debug/
├── __init__.py
├── apps.py
├── views.py              # HTTP views and API endpoints
├── consumers.py          # WebSocket consumer
├── urls.py              # URL routing
├── routing.py           # WebSocket routing
├── models.py            # (empty - no models needed)
├── admin.py            # (empty - no admin integration)
├── tests.py            # (placeholder)
├── migrations/          # (empty - no database changes)
├── templates/
│   └── dev_debug/
│       ├── base.html           # Base template
│       ├── agent_list.html     # Agent list view
│       └── agent_detail.html   # Agent detail view
└── static/
    └── dev_debug/
        ├── css/               # (placeholder)
        └── js/               # (JavaScript in templates)
```

### Integration Points

- **Core Models**: Uses existing `Agent` and `Service` models
- **Channel Groups**: Joins existing agent channel groups as passive listener
- **Authentication**: Uses Django's built-in authentication
- **URL Routing**: Integrated with main project URLs

### Event Listening Strategy

- **Agent Events**: Direct listener on agent WebSocket channels (`agent_{uuid}`)
- **Client Events**: Listener on client broadcast groups (`user_{id}_agent_status_updates`)
- **Raw Communication**: Full visibility of all agent traffic for debugging
- **Zero Core Impact**: No modifications to core application required

## 🔍 Debugging

### Common Issues

1. **WebSocket Connection Fails**
   - Check ASGI configuration
   - Verify Redis connection
   - Ensure `DEBUG=True`

2. **No Events Showing**
   - Verify agent is connected
   - Check WebSocket connection status
   - Ensure events are being generated

3. **Permission Denied**
   - Verify user is authenticated
   - Check if user owns the agent
   - Ensure `DEBUG=True`

### Log Monitoring

- WebSocket connections logged in console
- Event processing logged with timestamps
- Error handling with detailed messages

## 📊 Performance

### Optimizations

- **Efficient Queries**: `select_related` and `prefetch_related`
- **Connection Reuse**: Single WebSocket for multiple event types
- **Memory Management**: Limited event history (100 events max)
- **Polling Control**: User can disable polling

### Resource Usage

- **Minimal Database Load**: Uses existing APIs
- **Efficient WebSocket**: Binary message handling
- **Limited History**: Session-based event storage
- **User-Controlled**: Pause/resume capabilities

## 🌙 Developer-Friendly Dark Theme

**The debug dashboard features a comprehensive dark theme designed specifically for developers** who spend long hours monitoring systems:

- **Eye Comfort**: Dark backgrounds (`#0f172a`, `#1e293b`) reduce eye strain
- **High Contrast**: Light text (`#f1f5f9`, `#cbd5e1`) ensures excellent readability
- **Terminal Aesthetic**: Event logs use classic dark terminal styling
- **Status Colors**: Optimized for dark backgrounds with proper contrast
- **Modern Design**: Clean, professional dark interface throughout

## 🛠️ Troubleshooting

### WebSocket Connection Issues

If you experience WebSocket connection problems:

1. **Check Browser Console**: Look for detailed error messages
2. **Manual Reconnect**: Click the 🔄 button to force reconnection
3. **Connection Status**: Watch the connection indicator in top-right
4. **Network Tab**: Check for blocked connections in browser dev tools

### Common Issues & Solutions

- **Infinite Reconnect Loop**: Fixed with exponential backoff and max attempts
- **Firefox/Chrome Incompatibility**: Fixed with proper URL construction and error handling
- **Connection Drops**: Now handled gracefully with reconnection attempts
- **Debug Messages**: Include raw message data for advanced troubleshooting

### Advanced Debugging

The debug dashboard shows:
- **Raw Agent Traffic**: All WebSocket messages from agents
- **Parsed Events**: Structured event data for easy reading
- **Error Events**: Malformed message handling with full context
- **Connection Logs**: Detailed connection status and attempt history

## 🚨 Production Note

**This dashboard is development-only and will not be available in production environments.** 

All debug URLs and WebSocket endpoints are automatically disabled when `DEBUG=False`.

## 📝 Future Enhancements

Potential improvements for development convenience:

- Service status history graphs
- Agent performance metrics
- Event filtering and search
- Export capabilities for event logs
- Multiple agent monitoring in single view
- Agent command execution interface

---

*Built with Django, Channels, and modern web technologies for an optimal development debugging experience.*