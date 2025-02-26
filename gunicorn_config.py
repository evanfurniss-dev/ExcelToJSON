import os

# Bind to the port specified by Render's environment variable
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Configure number of worker processes
workers = 4

# Set timeout (in seconds)
timeout = 120

# Enable thread-based concurrency
threads = 2

# Reload workers when code changes (disable in production)
reload = False 