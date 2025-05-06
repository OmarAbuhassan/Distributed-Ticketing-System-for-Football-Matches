import { useState, useEffect, useRef, useCallback } from 'react';

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState({
    queue_stats: {},
    checkin_stats: {}
  });
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    wsRef.current = new WebSocket('ws://localhost:8003/ws');

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setDashboardData(data);
    };

    wsRef.current.onclose = () => {
      console.log('Dashboard WebSocket connection closed');
      // Attempt to reconnect after 2 seconds
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const formatTime = (minutes) => {
    if (!minutes || minutes < 0) return 'N/A';
    if (minutes < 60) {
      return `${Math.round(minutes)} mins`;
    }
    return `${Math.floor(minutes / 60)}h ${Math.round(minutes % 60)}m`;
  };

  return (
    <div className="p-6 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6">Real-time Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {Object.entries(dashboardData.queue_stats || {}).map(([matchId, categories]) => (
          <div key={matchId} className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-2xl font-semibold mb-4">Match {matchId}</h2>
            
            <div className="space-y-6">
              {/* Queue Statistics */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-xl font-semibold mb-3">Queue Statistics</h3>
                <div className="space-y-4">
                  {Object.entries(categories).map(([category, stats]) => (
                    <div key={category} className="border-b pb-2">
                      <h4 className="font-medium capitalize">{category}</h4>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="bg-white p-2 rounded">
                          <p className="text-gray-600">Queue Length</p>
                          <p className="text-2xl font-bold text-blue-600">
                            {stats.waiting_count}
                          </p>
                        </div>
                        <div className="bg-white p-2 rounded">
                          <p className="text-gray-600">Avg. Wait Time</p>
                          <p className="text-2xl font-bold text-green-600">
                            {formatTime(stats.avg_waiting_time)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Check-in Statistics */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-xl font-semibold mb-3">Check-in Statistics</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white p-3 rounded">
                    <p className="text-gray-600">Currently Checked In</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {dashboardData.checkin_stats[matchId]?.checked_in_count || 0}
                    </p>
                  </div>
                  <div className="bg-white p-3 rounded">
                    <p className="text-gray-600">Avg. Duration</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {formatTime(dashboardData.checkin_stats[matchId]?.avg_checkin_duration)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;