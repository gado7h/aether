"""
Aether - Core test execution logic
"""
import time
import requests
import json
import re
import os
from .utils import DEFAULT_TIMEOUT
from .bundler import get_testez_driver
from .config import get_api_url

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def resolve_source_map(text, source_map, verbose=False):
    """
    Resolve line numbers in text using source map and format stack traces.
    
    If verbose is False:
    - Hides lines that are NOT mapped (e.g. internal TaskScript lines).
    - Hides TestEZ internal lines unless they are part of the user's code.
    """
    if not source_map or not text:
        return text
    
    lines = text.split('\n')
    resolved_lines = []
    
    # Always keep the first line (the error message itself)
    # But try to resolve it too
    
    def resolve_line_content(line):
        # Helper to just resolve "TaskScript:123" -> "file.lua:10" in a string
        def replace_match(match):
            full_match = match.group(0)
            line_str = match.group(3)
            if not line_str: return full_match
            line_num = int(line_str)
            
            for mapping in source_map:
                if mapping["start"] <= line_num <= mapping["end"]:
                    offset = line_num - mapping["start"]
                    orig_line = mapping["original_start"] + offset
                    file_name = mapping["file"]
                    try:
                        file_name = os.path.relpath(file_name, os.getcwd())
                    except ValueError:
                        pass # Keep absolute if on different drive
                    return f"{file_name}:{orig_line}"
            return full_match
            
        def replace_roblox_match(match):
            full_match = match.group(0)
            line_num = int(match.group(2))
            for mapping in source_map:
                if mapping["start"] <= line_num <= mapping["end"]:
                    offset = line_num - mapping["start"]
                    orig_line = mapping["original_start"] + offset
                    file_name = mapping["file"]
                    try:
                        file_name = os.path.relpath(file_name, os.getcwd())
                    except ValueError:
                        pass
                    return f"{file_name}:{orig_line}"
            return full_match

        line = re.sub(r'(TaskScript)?(:)(\d+)', replace_match, line)
        line = re.sub(r'(Line )(\d+)', replace_roblox_match, line)
        return line

    # Process first line (Main error)
    if lines:
        resolved_lines.append(resolve_line_content(lines[0]))
        
        # Process stack trace
        if len(lines) > 1:
            resolved_lines.append("\n  Traceback:")
            
            for i, line in enumerate(lines[1:]):
                if not line.strip():
                    continue
                resolved = resolve_line_content(line)
                
                # Check if this line was mapped
                is_mapped = "TaskScript" not in resolved and "Line " not in resolved
                
                # If verbose, show everything.
                # If NOT verbose, only show mapped lines (user code).
                if verbose or is_mapped:
                    # Format it nicely
                    # Typically "Function name" might be at the end
                    resolved_lines.append(f"  at {resolved.strip()}")

    return "\n".join(resolved_lines)





def run_test(test_file, bundle, tests_dir, config, timeout=DEFAULT_TIMEOUT, verbose=False, source_map=None):

    """Execute a single test file on Roblox Cloud"""
    print(f"\n[Running Test: {test_file.name}]")
    start_time = time.time()
    
    api_url = get_api_url(config)
    api_key = config["api_key"]
    
    driver, spec_offset, spec_len = get_testez_driver(test_file, tests_dir)
    full_payload = bundle + "\n" + driver
    
    # Create a local source map copy extended with the test spec
    local_source_map = list(source_map) if source_map else []
    
    # Calculate absolute start line of the spec
    # Bundle lines + 1 (for joining newline) + spec_offset (lines into driver)
    bundle_lines = bundle.count('\n') + 1
    absolute_start = bundle_lines + spec_offset
    
    local_source_map.append({
        "file": str(test_file),
        "start": absolute_start,
        "end": absolute_start + spec_len - 1, # -1 because length includes start line
        "original_start": 1
    })
    
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
                print(f"\n{RED}[TIMEOUT]{RESET} Test exceeded {elapsed:.1f}s (limit: {timeout}s)")
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
                print(f"\n{RED}[ERROR]{RESET} Checking task status: {e}")
                return False
            
            if state == "COMPLETE":
                if "logs" in data and verbose:
                    print("\n[LOGS]")
                    for l in data["logs"]:
                        # Logs typically don't need strack trace filtering, but we can pass verbose=True to show everything
                        print(f"  > {resolve_source_map(l['message'], local_source_map, verbose=True)}")

                elapsed = time.time() - start_time
                output = data.get("output", {}).get("results", [{}])[0] or data.get("returnValue", {})
                
                # Check if there are any failures
                failure_count = output.get("failureCount", 0)
                has_failure = failure_count > 0
                
                # Display results
                if "results" in output and output["results"]:
                    print(f"\n[\"{test_file.stem}\"]:")
                    
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
                            # Always print errors for failures
                            for e in r["errors"]:
                                resolved_e = resolve_source_map(e, local_source_map, verbose)
                                print(f"{RED}  Error: {resolved_e}{RESET}")

                             
                elif output.get("status") == "Success" and not has_failure:
                    print(f"\n{GREEN}[SUCCESS]{RESET} Test Suite Passed")
                    
                else:
                    print(f"\n{RED}[FAILED]{RESET} Test Suite")
                    if has_failure:
                        print(f"   - {failure_count} test(s) failed")
                    fails = output.get("failures", [])
                    if fails:
                        for f in fails:
                            print(f"   - {resolve_source_map(f, local_source_map, verbose)}")
                
                print(f"[TIME] Completed in {elapsed:.2f}s")
                    
                # Check both status field and failureCount
                if output.get("status") in ("FAILED", "Failure") or has_failure:
                    return False
                return True
                
            elif state == "FAILED":
                elapsed = time.time() - start_time
                print(f"\n{RED}[ERROR]{RESET} Execution failed after {elapsed:.2f}s")
                resolved_msg = resolve_source_map(data.get('error', {}).get('message'), local_source_map, verbose)
                print(f"   - {resolved_msg}")


                if "logs" in data:
                    for l in data["logs"]:
                        print(f"      > {l['message']}")
                return False
                
    except Exception as e:
        print(f"{RED}[ERROR]{RESET} Request Failed: {e}")
        return False


def run_test_suite(args, files, bundle, tests_dir, config, source_map=None):

    """Execute a test suite"""
    import sys
    
    RESULTS_FILE = tests_dir / ".test-results"

    # --failed: Filter tests based on previous run
    if hasattr(args, 'failed') and args.failed:
        if RESULTS_FILE.exists():
            try:
                with open(RESULTS_FILE, "r") as f:
                    prev_results = json.load(f)
                    failed_specs = set(prev_results.get("failures", []))
                
                if not failed_specs:
                    print(f"{GREEN}[INFO]{RESET} No failed tests from last run.")
                    return 0
                
                original_count = len(files)
                files = [f for f in files if f.stem in failed_specs]
                print(f"{YELLOW}[INFO]{RESET} Re-running {len(files)} failed test(s) (out of {original_count})")
                
                if not files:
                    print(f"{YELLOW}[WARN]{RESET} Failed tests from last run no longer exist.")
                    return 0
            except Exception as e:
                print(f"{YELLOW}[WARN]{RESET} Could not load previous results: {e}")
        else:
            print(f"{YELLOW}[WARN]{RESET} No previous test results found. Running all tests.")

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
            print(f"{RED}[ERROR]{RESET} No test found matching '{args.test}'")
            return 1
    
    passed = 0
    failed = 0
    start_time = time.time()
    results = []
    failed_test_names = []
    
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
            failed_test_names.append(f.stem)
    
    total_time = time.time() - start_time
    total = passed + failed
    
    # Save results for --failed
    try:
        current_failures = failed_test_names
        # If we are running only a subset, we might want to merge with existing failures?
        # For simplicity, let's say the file tracks the LAST RUN's failures.
        # But if I fix one test and run with --failed, I expect others to remain?
        # A common pattern is: --failed only considers the *active* set.
        # However, to be robust, we probably just want to save what failed in THIS run.
        # Mechanism:
        # If running ALL: overwrite .test-results with current failures.
        # If running --failed: 
        #   failures = (previous_failures - passed_in_this_run) + new_failures_in_this_run
        
        all_failures = set(failed_test_names)
        
        if hasattr(args, 'failed') and args.failed and RESULTS_FILE.exists():
             # We need to remove tests that PASSED this time from the previous list
             try:
                 with open(RESULTS_FILE, "r") as f:
                     prev = json.load(f)
                     prev_fails = set(prev.get("failures", []))
                 
                 # Remove tests that were run and passed
                 for res in results:
                     if res["passed"] and res["name"] in prev_fails:
                         prev_fails.remove(res["name"])
                     elif not res["passed"]:
                         prev_fails.add(res["name"])
                         
                 all_failures = prev_fails
             except:
                 pass # Fallback to just current run failures
        
        with open(RESULTS_FILE, "w") as f:
            json.dump({"failures": list(all_failures), "last_run": time.time()}, f)
            
    except Exception as e:
        if args.verbose:
            print(f"{YELLOW}[WARN]{RESET} Could not save test results: {e}")

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
        summary_color = GREEN if failed == 0 else RED
        print(f"SUMMARY: {summary_color}{passed}/{total} passed{RESET}, {summary_color if failed > 0 else ''}{failed} failed{RESET}")
        print(f"Total time: {total_time:.2f}s")
        print("="*50)
    
    return 1 if failed > 0 else 0
