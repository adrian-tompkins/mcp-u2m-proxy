"""
HTML templates for the MCP proxy server
"""


def oauth_success_template(message: str) -> str:
    """Template for successful OAuth authentication"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentication Successful</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                background: white;
                padding: 3rem;
                border-radius: 1rem;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 500px;
            }}
            .success-icon {{
                font-size: 4rem;
                color: #10b981;
                margin-bottom: 1rem;
            }}
            h1 {{
                color: #1f2937;
                margin-bottom: 1rem;
            }}
            p {{
                color: #6b7280;
                font-size: 1.1rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✓</div>
            <h1>Authentication Successful!</h1>
            <p>{message}</p>
            <p style="margin-top: 2rem; font-size: 0.9rem;">
                The proxy server is now authenticated and ready to use.
            </p>
        </div>
    </body>
    </html>
    """


def oauth_error_template(message: str) -> str:
    """Template for failed OAuth authentication"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authentication Failed</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }}
            .container {{
                background: white;
                padding: 3rem;
                border-radius: 1rem;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 500px;
            }}
            .error-icon {{
                font-size: 4rem;
                color: #ef4444;
                margin-bottom: 1rem;
            }}
            h1 {{
                color: #1f2937;
                margin-bottom: 1rem;
            }}
            p {{
                color: #6b7280;
                font-size: 1.1rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">✗</div>
            <h1>Authentication Failed</h1>
            <p>{message}</p>
        </div>
    </body>
    </html>
    """

