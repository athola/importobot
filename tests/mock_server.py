"""A simple mock HTTP server for testing."""

import http.server
import socketserver

PORT = 8000


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
                    <label for="username_field">Username:</label><br>
                    <input type="text" id="username_field" name="username"><br>
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


def start_mock_server():
    """Start the mock server."""
    handler = MyHandler
    server = socketserver.TCPServer(("", PORT), handler)
    print(f"Serving mock server at port {PORT}")
    server.serve_forever()


def stop_mock_server(server):
    """Stop the mock server."""
    server.shutdown()
    server.server_close()
    print(f"Stopped mock server at port {PORT}")


if __name__ == "__main__":
    # This part is for manual testing of the server
    # In actual tests, it will be run in a separate thread
    start_mock_server()
