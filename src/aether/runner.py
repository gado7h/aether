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
    
    test_results = []
    has_suite_failure = False
    
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
                if not config.get("json"):
                    print(f"\n{RED}[TIMEOUT]{RESET} Test exceeded {elapsed:.1f}s (limit: {timeout}s)")
                return {
                    "success": False, 
                    "results": [{
                        "name": "Suite Timeout",
                        "status": "FAILED", 
                        "error": f"Test exceeded {elapsed:.1f}s limit",
                        "traceback": ""
                    }],
                    "duration": elapsed
                }
            
            if not config.get("json"):
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
                if not config.get("json"):
                    print(f"\n{RED}[ERROR]{RESET} Checking task status: {e}")
                return {
                    "success": False,
                    "results": [{
                        "name": "System Error",
                        "status": "FAILED",
                        "error": str(e),
                        "traceback": ""
                    }],
                    "duration": elapsed
                }
            
            if state == "COMPLETE":
                elapsed = time.time() - start_time
                output = data.get("output", {}).get("results", [{}])[0] or data.get("returnValue", {})
                
                # Check if there are any failures
                failure_count = output.get("failureCount", 0)
                has_suite_failure = failure_count > 0
                
                # --- LOGGING (only in non-json mode) ---
                if not config.get("json"):
                    if "logs" in data and verbose:
                        print("\n[LOGS]")
                        for l in data["logs"]:
                            print(f"  > {resolve_source_map(l['message'], local_source_map, verbose=True)}")

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
                                for e in r["errors"]:
                                    resolved_e = resolve_source_map(e, local_source_map, verbose)
                                    print(f"{RED}  Error: {resolved_e}{RESET}")
                                    
                    elif output.get("status") == "Success" and not has_suite_failure:
                        print(f"\n{GREEN}[SUCCESS]{RESET} Test Suite Passed")
                    else:
                        print(f"\n{RED}[FAILED]{RESET} Test Suite")
                        if has_suite_failure:
                            print(f"   - {failure_count} test(s) failed")
                        fails = output.get("failures", [])
                        if fails:
                            for f in fails:
                                print(f"   - {resolve_source_map(f, local_source_map, verbose)}")
                    
                    print(f"[TIME] Completed in {elapsed:.2f}s")
                
                # --- COLLECT RESULTS ---
                if "results" in output and output["results"]:
                    for r in output["results"]:
                        name = r.get("name", "Unknown")
                        res_status = r.get("status", "Unknown")
                        
                        # Map status to standardized strings
                        status_map = {
                            "Success": "PASSED",
                            "Failure": "FAILED",
                            "Skipped": "SKIPPED"
                        }
                        final_status = status_map.get(res_status, res_status.upper())
                        
                        error_msg = ""
                        traceback = ""
                        
                        if res_status == "Failure" and "errors" in r:
                            # Combine multiple errors if present
                            # resolve_source_map returns string with newlines if stack trace
                            raw_errors = r["errors"]
                            if raw_errors:
                                # We'll take the first error as the main 'error' and 'traceback' 
                                # or simple concatenation?
                                # The user example shows "error" and "traceback" as separate fields.
                                # Usually `resolve_source_map` gives us back a formatted string.
                                # We might need to split it if we want separate fields, or just put it all in one.
                                # User wanted: "error": "Expected...", "traceback": "file:line"
                                
                                # Let's parse the first resolved error
                                resolved_e = resolve_source_map(raw_errors[0], local_source_map, verbose=False) # Get clean path
                                
                                # Try to split message and traceback if possible
                                # resolve_source_map returns: "Message\n  Traceback:\n  at file:line"
                                parts = resolved_e.split("\n  Traceback:\n")
                                error_msg = parts[0]
                                if len(parts) > 1:
                                    # Clean up "  at " prefix
                                    traceback = parts[1].replace("  at ", "").strip()
                        
                        test_results.append({
                            "name": name,
                            "status": final_status,
                            "error": error_msg,
                            "traceback": traceback
                        })
                else:
                    # Fallback if no detailed results (e.g. script error or suite level failure)
                    # Use the 'failures' list from TestEZ
                    pass_suite = (output.get("status") == "Success" and not has_suite_failure)
                    if not pass_suite:
                        fails = output.get("failures", [])
                        msg = "Test Suite Failed"
                        if fails:
                             msg = "; ".join(fails)
                        
                        # If we have no individual tests but a suite failure, add a dummy fail
                        test_results.append({
                            "name": test_file.stem,
                            "status": "FAILED",
                            "error": msg,
                            "traceback": ""
                        })

                success = not (output.get("status") in ("FAILED", "Failure") or has_suite_failure)
                return {
                    "success": success,
                    "results": test_results,
                    "duration": elapsed
                }
                
            elif state == "FAILED":
                elapsed = time.time() - start_time
                resolved_msg = resolve_source_map(data.get('error', {}).get('message'), local_source_map, verbose)
                
                if not config.get("json"):
                    print(f"\n{RED}[ERROR]{RESET} Execution failed after {elapsed:.2f}s")
                    print(f"   - {resolved_msg}")
                    if "logs" in data:
                        for l in data["logs"]:
                            print(f"      > {l['message']}")
                            
                return {
                    "success": False,
                    "results": [{
                        "name": "Execution Error",
                        "status": "FAILED",
                        "error": resolved_msg,
                        "traceback": ""
                    }],
                    "duration": elapsed
                }
                
    except Exception as e:
        if not config.get("json"):
             print(f"{RED}[ERROR]{RESET} Request Failed: {e}")
        return {
            "success": False,
            "results": [{
                "name": "Request Failed",
                "status": "FAILED",
                "error": str(e),
                "traceback": ""
            }],
            "duration": 0
        }


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
    
    passed_count = 0
    failed_count = 0
    start_time = time.time()
    
    # Aggregated list of all test cases
    all_test_cases = []
    failed_files_set = set()
    
    # Sequential execution
    for f in files:
        # Resolve timeout
        to = args.timeout or config.get("timeout") or DEFAULT_TIMEOUT
        
        # Inject json flag into config so run_test knows whether to print
        config["json"] = args.json
        
        run_output = run_test(
            f, bundle, tests_dir, config, 
            timeout=to, 
            verbose=args.verbose,
            source_map=source_map
        )
        
        # Track failed files for --failed re-run capability
        if not run_output["success"]:
            failed_files_set.add(f.stem)
        
        # Collect individual test cases
        if run_output["results"]:
             all_test_cases.extend(run_output["results"])
        
        # Update counts based on individual tests
        for t in run_output["results"]:
            if t["status"] == "PASSED":
                passed_count += 1
            elif t["status"] == "FAILED":
                failed_count += 1
            
    total_time = time.time() - start_time
    total = passed_count + failed_count
    skipped_count = sum(1 for t in all_test_cases if t["status"] == "SKIPPED")
    total += skipped_count

    # Save results for --failed
    try:
        all_failures = failed_files_set
        
        if hasattr(args, 'failed') and args.failed and RESULTS_FILE.exists():
             # We need to remove tests that PASSED this time from the previous list
             try:
                 with open(RESULTS_FILE, "r") as f:
                     prev = json.load(f)
                     prev_fails = set(prev.get("failures", []))
                 
                 # Remove files that passed in this run
                 for f in files:
                     if f.stem in prev_fails and f.stem not in failed_files_set:
                         prev_fails.remove(f.stem)
                     elif f.stem in failed_files_set:
                         prev_fails.add(f.stem)
                         
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
            "summary": {
                "passed": passed_count,
                "failed": failed_count,
                "total": total,
                "duration": round(total_time, 2)
            },
            "tests": all_test_cases
        }
        print(json.dumps(output, indent=2))
    else:
        print("\n" + "="*50)
        summary_color = GREEN if failed_count == 0 else RED
        print(f"SUMMARY: {summary_color}{passed_count}/{total} passed{RESET}, {summary_color if failed_count > 0 else ''}{failed_count} failed{RESET}")
        print(f"Total time: {total_time:.2f}s")
        print("="*50)
    
    return 1 if failed_count > 0 else 0
