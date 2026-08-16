#!/usr/bin/env python3
"""
PII Dashboard Launcher
Script to launch the PII Analysis Dashboard.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def main():
    """Main function to launch the PII dashboard."""
    parser = argparse.ArgumentParser(description="Launch PII Analysis Dashboard")
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to run the Streamlit dashboard on (default: 8501)"
    )
    parser.add_argument(
        "--file",
        default="fast_pii_analysis_report.json",
        help="Path to the PII analysis report file (default: fast_pii_analysis_report.json)"
    )
    
    args = parser.parse_args()
    
    # Get the directory of this script
    script_dir = Path(__file__).parent.absolute()
    
    # Path to the dashboard app
    dashboard_path = script_dir / "dashboard" / "pii_dashboard" / "app.py"
    
    if not dashboard_path.exists():
        print(f"Error: Dashboard app not found at {dashboard_path}")
        sys.exit(1)
    
    # Check if the PII analysis file exists
    pii_file = Path(args.file)
    if not pii_file.exists() and not pii_file.is_absolute():
        # Try relative to script directory
        pii_file = script_dir / args.file
        if not pii_file.exists():
            print(f"Warning: PII analysis file not found at {args.file}")
            print("The dashboard will still launch, but you'll need to specify the file path in the UI.")
    
    # Launch the Streamlit app
    print(f"🚀 Launching PII Analysis Dashboard on port {args.port}...")
    print(f"📊 Dashboard URL: http://localhost:{args.port}")
    print("Press Ctrl+C to stop the dashboard")
    
    try:
        subprocess.run([
            "streamlit", "run", str(dashboard_path),
            "--server.port", str(args.port),
            "--",
            "--file", str(pii_file)
        ])
    except KeyboardInterrupt:
        print("\n✅ Dashboard stopped")
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()