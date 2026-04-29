#!/usr/bin/env python3
"""
Run the Alert Engine
====================
Starts both the event generator and alert engine for testing.

Usage:
    python run_alerts_engine.py                  # Run both engine and generator
    python run_alerts_engine.py --engine-only    # Run only the alert engine
    python run_alerts_engine.py --generator-only # Run only the event generator
    python run_alerts_engine.py --burst          # Generate burst events for testing
"""

import os
import sys
import time
import signal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.alert_engine import AlertEngineService, ALERTS_DB_PATH
from app.services.alert_events_generate import EventGenerator


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n[Main] Received interrupt signal, shutting down...")
    global running
    running = False


def check_database():
    """Check if database exists, initialize if not."""
    if not os.path.exists(ALERTS_DB_PATH):
        print(f"[Main] Database not found: {ALERTS_DB_PATH}")
        print("[Main] Initializing database...")
        
        engine = AlertEngineService()
        schema_path = os.path.join(os.path.dirname(__file__), "app", "files", "alerts_schema.sql")
        engine.initialize_db(schema_path)
        print("[Main] Database initialized!")
    else:
        print(f"[Main] Using existing database: {ALERTS_DB_PATH}")


def print_stats(engine: AlertEngineService):
    """Print current engine stats."""
    stats = engine.get_stats()
    active_alerts = engine.get_active_alerts()
    
    print("\n" + "="*50)
    print("ALERT ENGINE STATUS")
    print("="*50)
    print(f"  Engine Status: {stats['engine_status']}")
    print(f"  Total Events: {stats['total_events']}")
    print(f"  Total Metrics: {stats['total_metrics']}")
    print(f"  Active Alerts: {stats['active_alerts']}")
    print(f"  Total Triggered: {stats['total_alerts_triggered']}")
    print(f"  Last Processed ID: {stats['last_processed_id']}")
    
    if active_alerts:
        print("\n  🚨 ACTIVE ALERTS:")
        for alert in active_alerts:
            print(f"    - {alert['name']} ({alert['severity'].upper()})")
            print(f"      Table: {alert['table_name']} | Threshold: {alert['threshold']}")
    
    print("="*50 + "\n")


def run_burst_mode():
    """Run burst mode to trigger alerts for testing."""
    print("\n" + "="*60)
    print("BURST MODE - Generating events to trigger alerts")
    print("="*60 + "\n")
    
    generator = EventGenerator()
    engine = AlertEngineService()
    
    # Start engine first
    engine.start_background(tick_interval=0.5)
    time.sleep(1)
    
    print("[Burst] Choose burst type:")
    print("  1. Failed logins (triggers 'Failed Login Spike' alert)")
    print("  2. Failed transactions (triggers 'Failed Transaction Spike' alert)")
    print("  3. KYC rejections (triggers 'KYC Rejection Spike' alert)")
    print("  4. Transaction volume (triggers 'Transaction Volume Spike' alert)")
    print("  5. All of the above")
    
    try:
        choice = input("\nEnter choice (1-5): ").strip()
    except:
        choice = "5"
    
    if choice == "1":
        generator.generate_login_burst(count=15, status="failed")
    elif choice == "2":
        generator.generate_transaction_burst(count=10, status="failed")
    elif choice == "3":
        generator.generate_kyc_rejection_burst(count=5)
    elif choice == "4":
        generator.generate_transaction_burst(count=25, status="success")
    else:
        generator.generate_login_burst(count=15, status="failed")
        time.sleep(1)
        generator.generate_transaction_burst(count=10, status="failed")
        time.sleep(1)
        generator.generate_kyc_rejection_burst(count=5)
    
    # Wait for processing
    time.sleep(3)
    
    # Show stats
    print_stats(engine)
    
    # Show recent history
    history = engine.get_alert_history(limit=10)
    if history:
        print("\n📋 RECENT ALERT HISTORY:")
        print("-"*50)
        for h in history:
            icon = "🚨" if h['action'] == 'triggered' else "✅"
            print(f"  {icon} [{h['action'].upper()}] {h.get('metric_name', f'Metric #{h[\"metric_id\"]}')} ")
            print(f"      Count: {h['event_count']} | Threshold: {h['threshold']} | Time: {h['created_at']}")
    
    engine.stop()
    print("\n[Burst] Completed!")


def main():
    """Main entry point."""
    global running
    running = True
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    args = sys.argv[1:]
    
    engine_only = "--engine-only" in args
    generator_only = "--generator-only" in args
    burst_mode = "--burst" in args
    
    # Check database
    check_database()
    
    # Burst mode
    if burst_mode:
        run_burst_mode()
        return
    
    # Initialize services
    engine = AlertEngineService()
    generator = EventGenerator()
    
    print("\n" + "="*60)
    print("DERIVINSIGHT ALERT ENGINE")
    print("="*60)
    
    # Start services
    if not generator_only:
        print("[Main] Starting Alert Engine...")
        engine.start_background(tick_interval=1.0)
    
    if not engine_only:
        print("[Main] Starting Event Generator...")
        # Use faster intervals for demo
        generator.start_all(
            user_interval=60,        # 1 minute
            login_interval=(2, 8),   # 2-8 seconds
            txn_interval=(1, 3),     # 1-3 seconds
            kyc_interval=(5, 15)     # 5-15 seconds
        )
    
    print("\n[Main] System running. Press Ctrl+C to stop.\n")
    print("[Main] Stats will be printed every 30 seconds.\n")
    
    # Main loop
    last_stats_time = time.time()
    stats_interval = 30  # seconds
    
    while running:
        try:
            time.sleep(1)
            
            # Print stats periodically
            if time.time() - last_stats_time >= stats_interval:
                print_stats(engine)
                last_stats_time = time.time()
                
        except Exception as e:
            print(f"[Main] Error: {e}")
    
    # Shutdown
    print("\n[Main] Shutting down...")
    
    if not generator_only:
        engine.stop()
    
    if not engine_only:
        generator.stop_all()
    
    # Final stats
    print_stats(engine)
    
    print("[Main] Shutdown complete.")


if __name__ == "__main__":
    main()
