"""
Roblox Test Runner - Core test execution logic
"""
import time
import requests
import json
import re
from .utils import DEFAULT_TIMEOUT
from .bundler import get_testez_driver
from .config import get_api_url

def resolve_source_map(text, source_map):
    """Resolve line numbers in text using source map"""
    if not source_map or not text:
        return text
        
    def replace_line(match):
        # Allow matching ":123" or "Line 123"
        # Group 1: The prefix (e.g. ":", "Line ")
        # Group 2: The line number
        prefix = match.group(1)
        line_num = int(match.group(2))
        
        for mapping in source_map:
            if mapping["start"] <= line_num <= mapping["end"]:
                offset = line_num - mapping["start"]
                orig_line = mapping["original_start"] + offset
                file_name = mapping["file"]
                # Try to clean up file path relative to cwd if possible, but full path is fine
                # Make it look like a standard file reference
                
                # If it matched ":123", return ":10 (src/foo.luau)"
                # This helps user click it in VS Code usually? VS Code parsing needs "file:line"
                
                # We return "{file}:{line}"
                # If the prefix was "Line ", we change it to "{file}:{line}"
                
                return f"{prefix}{line_num} [{file_name}:{orig_line}]"
                
        return match.group(0)

    # Regex covers:
    # 1. :1234 (standard Lua trace)
    # 2. Line 1234 (Roblox script trace)
    # We use lookbehind or capturing groups carefully.
    
    # Matches ":123"
    text = re.sub(r'(:)(\d+)', replace_line, text)
    
    # Matches "Line 123"
    text = re.sub(r'(Line )(\d+)', replace_line, text)
    
    return text




def run_test(test_file, bundle, tests_dir, config, timeout=DEFAULT_TIMEOUT, verbose=False, source_map=None):

    """Execute a single test file on Roblox Cloud"""
    print(f"\n[Running Test: {test_file.name}]")
    start_time = time.time()
    
    api_url = get_api_url(config)
    api_key = config["api_key"]
    
    driver = get_testez_driver(test_file, tests_dir)
    full_payload = bundle + "\n" + driver
    
    print(f"Sending request (Payload: {len(full_payload)} chars)...")
    
    try:
        resp = requests.post(
            api_url,
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={"script": full_payload}
        )
        resp.raise_for_status()
        task = resp.json()
        task_id = task.get("path")
        
        elapsed = 0
        while True:
            time.sleep(2)
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                print(f"\n[TIMEOUT] Test exceeded {elapsed:.1f}s (limit: {timeout}s)")
                return False
            
            print(".", end="", flush=True)
            try:
                status_resp = requests.get(
                    f"https://apis.roblox.com/cloud/v2/{task_id}",
                    headers={"x-api-key": api_key}
                )
                status_resp.raise_for_status()
                data = status_resp.json()
                state = data.get("state")
            except requests.exceptions.RequestException as e:
                print(f"\n[ERROR] Checking task status: {e}")
                return False
            
            if state == "COMPLETE":
                if "logs" in data and verbose:
                    print("\n[LOGS]")
                    for l in data["logs"]:
                        print(f"  > {l['message']}")

                elapsed = time.time() - start_time
                output = data.get("output", {}).get("results", [{}])[0] or data.get("returnValue", {})
                
                # Check if there are any failures
                failure_count = output.get("failureCount", 0)
                has_failure = failure_count > 0
                
                # Display results
                if "results" in output and output["results"]:
                    print(f"\n[\"{test_file.stem}\"]:")
                    
                    # ANSI colors
                    GREEN = "\033[92m"
                    RED = "\033[91m"
                    YELLOW = "\033[93m"
                    RESET = "\033[0m"

                    for r in output["results"]:
                        name = r.get("name", "Unknown")
                        res_status = r.get("status", "Unknown")
                        
                        if res_status == "Success":
                            status_str = f"{GREEN}[PASSED]{RESET}"
                        elif res_status == "Failure":
                            status_str = f"{RED}[FAILED]{RESET}"
                        elif res_status == "Skipped":
                            status_str = f"{YELLOW}[SKIPPED]{RESET}"
                        else:
                            status_str = f"[{res_status}]"
                            
                        print(f"\"{name}\": {status_str}")
                        
                        if res_status == "Failure" and "errors" in r:
                            if verbose:
                                for e in r["errors"]:
                                    resolved_e = resolve_source_map(e, source_map)
                                    print(f"{RED}  Error: {resolved_e}{RESET}")

                             
                elif output.get("status") == "Success" and not has_failure:
                    print(f"\n[SUCCESS] Test Suite Passed")
                    
                else:
                    print(f"\n[FAILED] Test Suite")
                    if has_failure:
                        print(f"   - {failure_count} test(s) failed")
                    fails = output.get("failures", [])
                    if fails:
                        for f in fails:
                            print(f"   - {resolve_source_map(f, source_map)}")

                
                print(f"[TIME] Completed in {elapsed:.2f}s")
                    
                # Check both status field and failureCount
                if output.get("status") in ("FAILED", "Failure") or has_failure:
                    return False
                return True
                
            elif state == "FAILED":
                elapsed = time.time() - start_time
                print(f"\n[ERROR] Execution failed after {elapsed:.2f}s")
                resolved_msg = resolve_source_map(data.get('error', {}).get('message'), source_map)
                print(f"   - {resolved_msg}")

                if "logs" in data:
                    for l in data["logs"]:
                        print(f"      > {l['message']}")
                return False
                
    except Exception as e:
        print(f"[ERROR] Request Failed: {e}")
        return False


def run_test_suite(args, files, bundle, tests_dir, config, source_map=None):

    """Execute a test suite"""
    import sys
    
    # Filter tests if specific name provided
    if args.test != "all":
        target = args.test.lower()
        found = None
        for f in files:
            if target in f.name.lower():
                found = f
                break
        
        if found:
            files = [found]
        else:
            print(f"[ERROR] No test found matching '{args.test}'")
            return 1
    
    passed = 0
    failed = 0
    start_time = time.time()
    results = []
    
    # Sequential execution
    for f in files:
        # Resolve timeout: args.timeout (CLI) > config["timeout"] > DEFAULT_TIMEOUT
        to = args.timeout or config.get("timeout") or DEFAULT_TIMEOUT
        success = run_test(
            f, bundle, tests_dir, config, 
            timeout=to, 
            verbose=args.verbose,
            source_map=source_map
        )
        result = {"name": f.stem, "passed": success, "file": str(f)}
        results.append(result)
        if success:
            passed += 1
        else:
            failed += 1
    
    total_time = time.time() - start_time
    total = passed + failed
    
    # Output results
    if args.json:
        output = {
            "passed": passed,
            "failed": failed,
            "total": total,
            "time": round(total_time, 2),
            "tests": results
        }
        print(json.dumps(output, indent=2))
    else:
        print("\n" + "="*50)
        print(f"SUMMARY: {passed}/{total} passed, {failed} failed")
        print(f"Total time: {total_time:.2f}s")
        print("="*50)
    
    return 1 if failed > 0 else 0
