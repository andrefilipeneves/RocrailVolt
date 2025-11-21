import os
from apps import create_app
from config import Config


def get_port():
    """Determine port from environment or default to 5000."""
    return int(os.environ.get("PORT", os.environ.get("FLASK_RUN_PORT", 5000)))


def get_debug():
    """Determine debug mode from FLASK_DEBUG env var (defaults to False)."""
    return os.environ.get("FLASK_DEBUG", "0") == "1"


# Create the Flask application using the Config class
app = create_app(Config)

if __name__ == '__main__':
    port = get_port()
    debug = get_debug()
    # Run the app on 0.0.0.0 to be accessible externally if needed
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
