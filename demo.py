"""
Demonstration script showing sub-pub capabilities
"""
import subprocess
import sys
import time


def run_demo(config_file, mode_name, duration=5):
    """Run a demo of sub-pub for a specified duration"""
    print(f"\n{'='*70}")
    print(f"DEMO: {mode_name} Mode")
    print(f"Config: {config_file}")
    print(f"Duration: {duration} seconds")
    print('='*70)
    
    try:
        result = subprocess.run(
            ['python', '-m', 'sub_pub.main', '-c', config_file, '-l', 'INFO'],
            timeout=duration,
            capture_output=True,
            text=True
        )
    except subprocess.TimeoutExpired as e:
        output = e.stdout.decode('utf-8') if isinstance(e.stdout, bytes) else e.stdout
        
        print(output)
        
        # Extract and highlight metrics
        if "Final metrics:" in output:
            print("\n" + "="*70)
            print("METRICS SUMMARY")
            print("="*70)
            lines = output.split('\n')
            in_metrics = False
            for line in lines:
                if "Final metrics:" in line:
                    in_metrics = True
                if in_metrics:
                    print(line)
        
        print("\n" + "="*70)
        print(f"✓ Demo completed successfully")
        print("="*70)
        
        return True
    except Exception as e:
        print(f"✗ Error running demo: {e}")
        return False


def main():
    """Run demonstrations"""
    print("="*70)
    print("SUB-PUB: Extreme Performance Pub-Sub Message Processor")
    print("="*70)
    print("\nThis demonstration will:")
    print("  1. Show One-to-One mode with mock adapters")
    print("  2. Display real-time message processing")
    print("  3. Show comprehensive metrics")
    print()
    
    input("Press Enter to start the demonstration...")
    
    # Demo one-to-one mode
    run_demo('examples/mock-config.yaml', 'One-to-One (Mock)', duration=5)
    
    print("\n\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey Features Demonstrated:")
    print("  ✓ Thread-based parallel processing")
    print("  ✓ Real-time message consumption and publishing")
    print("  ✓ Comprehensive metrics collection")
    print("  ✓ Per-topic tracking (source and destination)")
    print("  ✓ Message rate calculation")
    print("  ✓ Clean shutdown with metrics reporting")
    print("\nNext Steps:")
    print("  1. Explore example configurations in 'examples/' directory")
    print("  2. Create custom processors (see examples/custom_processors.py)")
    print("  3. Configure for your message systems (Kafka, Pulsar, etc.)")
    print("  4. Tune thread pools and back-pressure settings")
    print("  5. Monitor with metrics for Grafana dashboards")
    print()


if __name__ == '__main__':
    main()
