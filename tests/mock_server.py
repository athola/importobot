"""A simple mock HTTP server for testing."""

import http.server
import socketserver

from importobot.config import TEST_SERVER_PORT

LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Login Page</title>
</head>
<body>
    <h1>Login Page</h1>
    <form id="loginForm">
        <input type="text" id="username" name="username" placeholder="Username">
        <input type="password" id="password" name="password" placeholder="Password">
        <button type="submit" id="loginButton">Login</button>
    </form>
    <div id="message" style="display:none;">Login Successful</div>
</body>
<script>
    document.getElementById('loginForm').addEventListener('submit', function(e) {
        e.preventDefault();
        document.getElementById('message').style.display = 'block';
    });
</script>
</html>
"""


class MyHandler(http.server.SimpleHTTPRequestHandler):
    """A simple handler for the mock server."""

    def do_GET(self):
        """Handle GET requests for the mock server."""
        if self.path in {"/login.html", "/"}:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(LOGIN_PAGE_HTML.encode("utf-8"))
        else:
            super().do_GET()

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin,unused-argument
        """Suppress default logging to keep test output clean."""
        return


def start_mock_server(server_port=None):
    """Start the mock server.

    Args:
        port: Port to bind to. If None, uses TEST_SERVER_PORT from config.
               If 0, dynamically allocates an available port.

    Returns:
        tuple: (server_instance, actual_port_used)
    """
    handler = MyHandler
    if server_port is None:
        server_port = TEST_SERVER_PORT

    server = socketserver.TCPServer(("", server_port), handler)
    actual_port = server.server_address[1]
    print(f"Serving mock server at port {actual_port}")
    return server, actual_port


def stop_mock_server(mock_server):
    """Stop the mock server."""
    port = mock_server.server_address[1]
    mock_server.shutdown()
    mock_server.server_close()
    print(f"Stopped mock server at port {port}")


if __name__ == "__main__":
    # This part is for manual testing of the server
    # In actual tests, it will be run in a separate thread
    test_server, test_port = start_mock_server()  # type: ignore[no-untyped-call]
    try:
        test_server.serve_forever()
    except KeyboardInterrupt:
        stop_mock_server(test_server)  # type: ignore[no-untyped-call]
