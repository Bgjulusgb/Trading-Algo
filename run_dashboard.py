#!/usr/bin/env python3
"""
Startup script for the Trading Dashboard
"""

import sys
import os
import subprocess
import argparse

def main():
    """Main function to start the dashboard"""
    parser = argparse.ArgumentParser(description='Trading Dashboard')
    parser.add_argument('--port', type=int, default=8501,
                       help='Port to run dashboard on (default: 8501)')
    parser.add_argument('--host', default='localhost',
                       help='Host to bind to (default: localhost)')
    
    args = parser.parse_args()
    
    print("🌐 Starting Trading Dashboard...")
    print(f"🔗 URL: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the dashboard")
    print("=" * 50)
    
    try:
        # Start Streamlit dashboard
        cmd = [
            sys.executable, "-m", "streamlit", "run", "dashboard.py",
            "--server.port", str(args.port),
            "--server.address", args.host,
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()