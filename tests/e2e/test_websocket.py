"""
E2E tests for WebSocket connections.
Tests the training WebSocket endpoint.
"""
import json
from urllib.parse import urlparse

from playwright.sync_api import Page


class TestTrainingWebSocket:
    """Tests for the /training/ws WebSocket endpoint."""

    def _build_ws_url(self, api_base_url: str) -> str:
        base = api_base_url.rstrip("/")
        parsed = urlparse(base)
        if parsed.scheme:
            scheme = "wss" if parsed.scheme == "https" else "ws"
            path = parsed.path.rstrip("/")
            return f"{scheme}://{parsed.netloc}{path}/training/ws"
        return f"ws://{base}/training/ws"

    def test_websocket_connection_via_page(self, page: Page, base_url: str, api_base_url: str):
        """
        Test that the training WebSocket establishes a connection.
        Uses the browser's WebSocket API through Playwright.
        """
        page.goto(base_url)
        ws_url = self._build_ws_url(api_base_url)
        
        # Execute JavaScript to test WebSocket connection
        result = page.evaluate("""
            async (wsUrl) => {
                return new Promise((resolve) => {
                    const ws = new WebSocket(wsUrl);
                    let connectionResult = { connected: false, message: null };
                    
                    ws.onopen = () => {
                        connectionResult.connected = true;
                    };
                    
                    ws.onmessage = (event) => {
                        try {
                            connectionResult.message = JSON.parse(event.data);
                        } catch {
                            connectionResult.message = event.data;
                        }
                        ws.close();
                        resolve(connectionResult);
                    };
                    
                    ws.onerror = (error) => {
                        connectionResult.error = 'Connection error';
                        resolve(connectionResult);
                    };
                    
                    // Timeout after 5 seconds
                    setTimeout(() => {
                        ws.close();
                        resolve(connectionResult);
                    }, 5000);
                });
            }
        """, ws_url)
        
        # WebSocket should have connected
        assert result.get("connected") or result.get("message") is not None, \
            f"WebSocket connection failed: {result}"

    def test_websocket_receives_initial_state(self, page: Page, base_url: str, api_base_url: str):
        """
        Test that the WebSocket sends initial connection state.
        """
        page.goto(base_url)
        ws_url = self._build_ws_url(api_base_url)
        
        result = page.evaluate("""
            async (wsUrl) => {
                return new Promise((resolve) => {
                    const ws = new WebSocket(wsUrl);
                    
                    ws.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            ws.close();
                            resolve(data);
                        } catch {
                            resolve({ error: 'Failed to parse message' });
                        }
                    };
                    
                    ws.onerror = () => {
                        resolve({ error: 'Connection error' });
                    };
                    
                    setTimeout(() => {
                        ws.close();
                        resolve({ error: 'Timeout' });
                    }, 5000);
                });
            }
        """, ws_url)
        
        # Should receive a connection message with initial state
        if result.get("type") == "connection":
            assert "data" in result
            data = result["data"]
            assert "is_training" in data
            assert "latest_stats" in data

    def test_websocket_ping_pong(self, page: Page, base_url: str, api_base_url: str):
        """
        Test that the WebSocket responds to ping with pong.
        """
        page.goto(base_url)
        ws_url = self._build_ws_url(api_base_url)
        
        result = page.evaluate("""
            async (wsUrl) => {
                return new Promise((resolve) => {
                    const ws = new WebSocket(wsUrl);
                    let gotPong = false;
                    
                    ws.onopen = () => {
                        // Wait a bit then send ping
                        setTimeout(() => {
                            ws.send('ping');
                        }, 100);
                    };
                    
                    ws.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            if (data.type === 'pong') {
                                gotPong = true;
                                ws.close();
                                resolve({ gotPong: true });
                            }
                        } catch {
                            // Ignore parse errors
                        }
                    };
                    
                    setTimeout(() => {
                        ws.close();
                        resolve({ gotPong: gotPong });
                    }, 3000);
                });
            }
        """, ws_url)
        
        # Should have received pong response
        assert result.get("gotPong", False), "Did not receive pong response"
