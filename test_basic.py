"""Simple test script to verify sub-pub functionality"""
import time
import subprocess
import sys


def test_mode(config_file, mode_name):
    """Test a specific mode by running it for a few seconds"""
    print(f"\n{'='*60}")
    print(f"Testing {mode_name} mode with {config_file}")
    print('='*60)
    
    try:
        # Run for 3 seconds
        result = subprocess.run(
            ['python', '-m', 'sub_pub.main', '-c', config_file, '-l', 'INFO'],
            timeout=3,
            capture_output=True,
            text=True
        )
    except subprocess.TimeoutExpired as e:
        # This is expected - we're timing out to stop the process
        output = e.stdout.decode('utf-8') if e.stdout else ""
        print(output)
        
        # Check for successful startup
        if "flow started" in output.lower():
            print(f"✓ {mode_name} mode started successfully")
            return True
        else:
            print(f"✗ {mode_name} mode failed to start")
            error_output = e.stderr.decode('utf-8') if e.stderr else 'None'
            print(f"Error output: {error_output}")
            return False
    except Exception as e:
        print(f"✗ Error testing {mode_name}: {e}")
        return False


def main():
    """Run all tests"""
    print("Sub-Pub Functionality Test")
    print("="*60)
    
    results = {}
    
    # Test mock config (one-to-one mode)
    results['one-to-one'] = test_mode('examples/mock-config.yaml', 'One-to-One')
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for mode, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{mode:20s}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
