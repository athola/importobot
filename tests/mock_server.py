"""A simple mock HTTP server for testing."""

import http.server
import socketserver

from importobot.config import TEST_SERVER_PORT


class MyHandler(http.server.SimpleHTTPRequestHandler):
    """A simple handler for the mock server."""

    def do_GET(self):
        """Handle GET requests for the mock server."""
        if self.path == "/login.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login Page</title>
            </head>
            <body>
                <h1>Login</h1>
                <form>
                    <label for="username">Username:</label><br>
                    <input type="text" id="username" name="username"><br>
                    <label for="password_field">Password:</label><br>
                    <input type="password" id="password_field" name="password"><br><br>
                    <button type="button" id="login_button">Login</button>
                </form>
                <p id="status_message"></p>
                <script>
                    document.getElementById('login_button').onclick = function() {
                        document.getElementById('status_message').innerText = (
                            'Login successful!'
                        );
                    };
                </script>
            </body>
            </html>
            """
            self.wfile.write(html_content.encode("utf-8"))
        else:
            super().do_GET()


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
    test_server, test_port = start_mock_server()
    try:
        test_server.serve_forever()
    except KeyboardInterrupt:
        stop_mock_server(test_server)
