"""
Aether - Core test execution logic
"""
import time
import requests
import json
import re
import os
from .utils import DEFAULT_TIMEOUT
from .bundler import get_testez_driver, get_master_driver
from .config import get_api_url

from .ui import console

def resolve_source_map(text, source_map, verbose=False):
    """
    Resolve line numbers in text using source map and format stack traces.
    """
    if not source_map or not text:
        return text
    
    lines = text.split('\n')
    resolved_lines = []
    
    def resolve_line_content(line):
        def replace_match(match):
            full_match = match.group(0)
            line_str = match.group(3)
            if not line_str:
                return full_match
            line_num = int(line_str)
            
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

    if lines:
        resolved_lines.append(resolve_line_content(lines[0]))
        
        if len(lines) > 1:
            resolved_lines.append("\n  Traceback:")
            
            for i, line in enumerate(lines[1:]):
                if not line.strip():
                    continue
                resolved = resolve_line_content(line)
                is_mapped = "TaskScript" not in resolved and "Line " not in resolved
                if verbose or is_mapped:
                    resolved_lines.append(f"  at {resolved.strip()}")

    return "\n".join(resolved_lines)


def run_test(test_file, bundle, tests_dir, config, timeout=DEFAULT_TIMEOUT, verbose=False, source_map=None):
    """Execute a single test file on Roblox Cloud"""
    # print(f"\n[Running Test: {test_file.name}]")
    start_time = time.time()
    
    api_url = get_api_url(config)
    api_key = config["api_key"]
    
    driver, spec_offset, spec_len = get_testez_driver(test_file, tests_dir)
    full_payload = bundle + "\n" + driver
    
    local_source_map = list(source_map) if source_map else []
    bundle_lines = bundle.count('\n') + 1
    absolute_start = bundle_lines + spec_offset
    
    local_source_map.append({
        "file": str(test_file),
        "start": absolute_start,
        "end": absolute_start + spec_len - 1,
        "original_start": 1
    })
    
    # print(f"Sending request (Payload: {len(full_payload)} chars)...")
    
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
                    console.print(f"\n[red][TIMEOUT][/red] Test exceeded {elapsed:.1f}s (limit: {timeout}s)")
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
                pass
                
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
                    console.print(f"\n[red][ERROR][/red] Checking task status: {e}")
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
                
                failure_count = output.get("failureCount", 0)
                has_suite_failure = failure_count > 0
                
                if "results" in output and output["results"]:
                    for r in output["results"]:
                        name = r.get("name", "Unknown")
                        res_status = r.get("status", "Unknown")
                        
                        status_map = {
                            "Success": "PASSED",
                            "Failure": "FAILED",
                            "Skipped": "SKIPPED"
                        }
                        final_status = status_map.get(res_status, res_status.upper())
                        
                        error_msg = ""
                        traceback = ""
                        
                        if res_status == "Failure" and "errors" in r:
                            raw_errors = r["errors"]
                            if raw_errors:
                                resolved_e = resolve_source_map(raw_errors[0], local_source_map, verbose=False)
                                parts = resolved_e.split("\n  Traceback:\n")
                                error_msg = parts[0]
                                # Clean up redundant file path
                                error_msg = re.sub(r"^.*?\.spec\.luau:\d+:\s*", "", error_msg)
                                error_msg = re.sub(r"^Error:\s*", "", error_msg)
                                if len(parts) > 1:
                                    traceback = parts[1].replace("  at ", "").strip()
                        
                        test_results.append({
                            "name": name,
                            "status": final_status,
                            "error": error_msg,
                            "traceback": traceback
                        })
                else:
                    pass_suite = (output.get("status") == "Success" and not has_suite_failure)
                    if not pass_suite:
                        fails = output.get("failures", [])
                        msg = "Test Suite Failed"
                        if fails:
                             msg = "; ".join(fails)
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
                    console.print(f"\n[red][ERROR][/red] Execution failed after {elapsed:.2f}s")
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
             console.print(f"[red][ERROR][/red] Request Failed: {e}")
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


def run_tests_batch(files, bundle, tests_dir, config, timeout=DEFAULT_TIMEOUT, verbose=False, source_map=None):
    """Execute all test files in a single Roblox Cloud request (batch mode)"""
    # Silent start - spinner handles status
    start_time = time.time()
    
    api_url = get_api_url(config)
    api_key = config["api_key"]
    
    driver, spec_offsets = get_master_driver(files, tests_dir)
    full_payload = bundle + "\n" + driver
    
    local_source_map = list(source_map) if source_map else []
    bundle_lines = bundle.count('\n') + 1
    
    for offset_info in spec_offsets:
        abs_start = bundle_lines + offset_info["start"]
        abs_end = bundle_lines + offset_info["end"]
        local_source_map.append({
            "file": str(offset_info["file"]),
            "start": abs_start,
            "end": abs_end,
            "original_start": offset_info["original_start"]
        })
        
    # console.print(f" * Running: {len(files)} test file(s) in batch mode ...")
    
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
            time.sleep(1)
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                if not config.get("json"):
                    console.print(f"\n[red][TIMEOUT][/red] Batch exceeded {elapsed:.1f}s (limit: {timeout}s)")
                return {"success": False, "results": [], "duration": elapsed, "error": "Timeout"}
            
            if not config.get("json"):
                pass
                
            try:
                status_resp = requests.get(
                    f"https://apis.roblox.com/cloud/v2/{task_id}",
                    headers={"x-api-key": api_key}
                )
                status_resp.raise_for_status()
                data = status_resp.json()
                state = data.get("state")
            except Exception as e:
                return {"success": False, "results": [], "duration": elapsed, "error": str(e)}
            
            if state == "COMPLETE":
                elapsed = time.time() - start_time
                output = data.get("output", {}).get("results", [{}])[0] or data.get("returnValue", {})
                
                failure_count = output.get("failureCount", 0)
                has_suite_failure = failure_count > 0
                
                if not config.get("json") and "logs" in data and verbose:
                    print("\n[LOGS]")
                    for l in data["logs"]:
                         print(f"  > {resolve_source_map(l['message'], local_source_map, verbose=True)}")

                test_results = []
                if "results" in output and output["results"]:
                    for r in output["results"]:
                        name = r.get("name", "Unknown")
                        res_status = r.get("status", "Unknown")
                        status_map = {"Success": "PASSED", "Failure": "FAILED", "Skipped": "SKIPPED"}
                        final_status = status_map.get(res_status, res_status.upper())
                        
                        error_msg = ""
                        traceback = ""
                        if res_status == "Failure" and "errors" in r:
                            raw_errors = r["errors"]
                            if raw_errors:
                                resolved_e = resolve_source_map(raw_errors[0], local_source_map, verbose=False)
                                parts = resolved_e.split("\n  Traceback:\n")
                                error_msg = parts[0]
                                # Clean up redundant file path
                                error_msg = re.sub(r"^.*?\.spec\.luau:\d+:\s*", "", error_msg)
                                error_msg = re.sub(r"^Error:\s*", "", error_msg)
                                if len(parts) > 1:
                                    traceback = parts[1].replace("  at ", "").strip()
                        
                        test_results.append({
                            "name": name,
                            "status": final_status,
                            "error": error_msg,
                            "traceback": traceback
                        })
                else:
                    if output.get("status") == "FAILED" or has_suite_failure:
                         fails = output.get("failures", [])
                         msg = "; ".join(fails) if fails else "Unknown Batch Logic Error"
                         test_results.append({
                             "name": "Batch Suite",
                             "status": "FAILED",
                             "error": msg,
                             "traceback": ""
                         })

                success = not (output.get("status") in ("FAILED", "Failure") or has_suite_failure)
                
                # Since we can't reliably match test names to files, 
                # count files based on test results:
                # - If there are any FAILED tests, count as 1 file failed
                # - If there are any PASSED tests (and none failed), count as 1 file passed  
                # This is a simplification since batch mode combines all tests
                has_passing = any(r.get("status") == "PASSED" for r in test_results)
                has_failing = any(r.get("status") == "FAILED" for r in test_results)
                
                # For accurate file counts, we'd need TestEZ to report file source
                # For now, estimate: if we have mixed results, assume some files pass and some fail
                if has_failing and has_passing:
                    # Mixed results - can't determine exact file ownership, make best guess
                    # Use ratio of passed/failed tests to estimate file status
                    failed_tests = sum(1 for r in test_results if r.get("status") == "FAILED")
                    passed_tests = sum(1 for r in test_results if r.get("status") == "PASSED")
                    total_tests = failed_tests + passed_tests
                    
                    # Rough estimate: files_failed = ceil(files * failed_ratio)
                    if total_tests > 0:
                        fail_ratio = failed_tests / total_tests
                        estimated_failed = max(1, int(len(files) * fail_ratio + 0.5))
                        files_failed_count = min(estimated_failed, len(files) - 1)
                        files_passed_count = len(files) - files_failed_count
                    else:
                        files_failed_count = 0
                        files_passed_count = len(files)
                elif has_failing:
                    files_failed_count = len(files)
                    files_passed_count = 0
                else:
                    files_failed_count = 0
                    files_passed_count = len(files)
                
                return {
                    "success": success, 
                    "results": test_results, 
                    "duration": elapsed,
                    "files_failed": files_failed_count,
                    "files_passed": files_passed_count
                }
                
            elif state == "FAILED":
                elapsed = time.time() - start_time
                resolved_msg = resolve_source_map(data.get('error', {}).get('message'), local_source_map, verbose)
                return {"success": False, "results": [], "duration": elapsed, "error": resolved_msg}

    except Exception as e:
        return {"success": False, "results": [], "duration": 0, "error": str(e)}


def run_test_suite(args, files, bundle, tests_dir, config, source_map=None, batch_mode=False):
    """Execute a test suite (sequential or batch mode)"""
    import sys
    
    RESULTS_FILE = tests_dir / ".test-results"

    if hasattr(args, 'failed') and args.failed:
        if RESULTS_FILE.exists():
            try:
                with open(RESULTS_FILE, "r") as f:
                    prev_results = json.load(f)
                    failed_specs = set(prev_results.get("failures", []))
                
                if not failed_specs:
                    console.print("[green][INFO][/green] No failed tests from last run.")
                    return 0
                
                original_count = len(files)
                files = [f for f in files if f.stem in failed_specs]
                console.print(f"[yellow][INFO][/yellow] Re-running {len(files)} failed test(s) (out of {original_count})")
                
                if not files:
                    console.print("[yellow][WARN][/yellow] Failed tests from last run no longer exist.")
                    return 0
            except Exception as e:
                console.print(f"[yellow][WARN][/yellow] Could not load previous results: {e}")
        else:
            console.print("[yellow][WARN][/yellow] No previous test results found. Running all tests.")

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
            console.print(f"[red][ERROR][/red] No test found matching '{args.test}'")
            return 1
    
    passed_count = 0
    failed_count = 0
    start_time = time.time()
    all_test_cases = []
    failed_files_set = set()
    
    config["json"] = args.json
    to = args.timeout or config.get("timeout") or DEFAULT_TIMEOUT
    
    if batch_mode and len(files) > 1:
        # Batch execution
        if len(files) > 5:
            to = max(to, 30)
        
        run_output = run_tests_batch(
            files, bundle, tests_dir, config,
            timeout=to,
            verbose=args.verbose,
            source_map=source_map
        )
        
        if run_output.get("error"):
            if not args.json:
                console.print(f"\n[red][ERROR][/red] {run_output['error']}")
        
        for r in run_output["results"]:
            all_test_cases.append(r)
            if r["status"] == "PASSED":
                passed_count += 1
            elif r["status"] == "FAILED":
                failed_count += 1
                for f in files:
                    failed_files_set.add(f.stem)
    else:
        # Sequential execution (original behavior)
        for f in files:
            run_output = run_test(
                f, bundle, tests_dir, config, 
                timeout=to, 
                verbose=args.verbose,
                source_map=source_map
            )
            
            if not run_output["success"]:
                failed_files_set.add(f.stem)
            
            if run_output["results"]:
                 all_test_cases.extend(run_output["results"])
                 # Minimalist printing for sequential mode
                 if not args.json:
                     for r in run_output["results"]:
                         name = r["name"]
                         status = r["status"]
                         if status == "PASSED":
                             console.print(f"[bold green]PASS[/bold green]  {name}")
                         elif status == "FAILED":
                             console.print(f"[bold red]FAIL[/bold red]  {name}")
                             if r["error"]:
                                 console.print(f"      {r['error']}")
                             if r.get("traceback"):
                                 for line in r["traceback"].split("\n"):
                                     if line.strip():
                                         clean_line = line.strip()
                                         if not clean_line.startswith("at "):
                                              console.print(f"      [dim]at {clean_line}[/dim]")
                                         else:
                                              console.print(f"      [dim]{clean_line}[/dim]")
                         else:
                             console.print(f"[bold yellow]SKIP[/bold yellow]  {name}")
            
            for t in run_output["results"]:
                if t["status"] == "PASSED":
                    passed_count += 1
                elif t["status"] == "FAILED":
                    failed_count += 1
            
    total_time = time.time() - start_time
    total = passed_count + failed_count
    skipped_count = sum(1 for t in all_test_cases if t["status"] == "SKIPPED")
    total += skipped_count

    try:
        all_failures = failed_files_set
        
        if hasattr(args, 'failed') and args.failed and RESULTS_FILE.exists():
             try:
                 with open(RESULTS_FILE, "r") as f:
                     prev = json.load(f)
                     prev_fails = set(prev.get("failures", []))
                 
                 for f in files:
                     if f.stem in prev_fails and f.stem not in failed_files_set:
                         prev_fails.remove(f.stem)
                     elif f.stem in failed_files_set:
                         prev_fails.add(f.stem)
                         
                 all_failures = prev_fails
             except:
                 pass
        
        with open(RESULTS_FILE, "w") as f:
            json.dump({"failures": list(all_failures), "last_run": time.time()}, f)
            
    except Exception as e:
        if args.verbose:
            console.print(f"[yellow][WARN][/yellow] Could not save test results: {e}")

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
        if batch_mode and len(files) > 1:
            console.print()
            for r in all_test_cases:
                name = r["name"]
                status = r["status"]
                if status == "PASSED":
                    # PASS  test_name
                    console.print(f"[bold green]PASS[/bold green]  {name}")
                elif status == "FAILED":
                    # FAIL  test_name
                    console.print(f"[bold red]FAIL[/bold red]  {name}")
                    if r["error"]:
                        # Indented error without bullets
                        console.print(f"      {r['error']}")
                    if r.get("traceback"):
                        # Indented traceback, simplified
                        # console.print() # Compact
                        for line in r["traceback"].split("\n"):
                            if line.strip():
                                clean_line = line.strip()
                                # Format nicely if possible, or just print dim
                                if not clean_line.startswith("at "):
                                     console.print(f"      [dim]at {clean_line}[/dim]")
                                else:
                                     console.print(f"      [dim]{clean_line}[/dim]")
                else:
                    console.print(f"[bold yellow]SKIP[/bold yellow]  {name}")
            
            console.print()
            console.print("-" * 60, style="dim")
            
            # Calculate file pass/fail based on return value
            files_failed = run_output.get("files_failed", failed_count)
            files_passed = run_output.get("files_passed", len(files) - files_failed)
            
            # Minimalist Summary
            parts = []
            if files_failed > 0:
                parts.append(f"[red]{files_failed} failed[/red]")
            parts.append(f"{files_passed} passed")
            parts.append(f"{len(files)} total")
            console.print(f"Test Files:  {', '.join(parts)}")
            
            parts = []
            if failed_count > 0:
                parts.append(f"[red]{failed_count} failed[/red]")
            parts.append(f"{passed_count} passed")
            parts.append(f"{total} total")
            console.print(f"Tests:       {', '.join(parts)}")
            
            console.print(f"Time:        {total_time:.2f}s")
        else:
            console.print()
            console.print("-" * 60, style="dim")
            
            parts = []
            if failed_count > 0:
                parts.append(f"[red]{failed_count} failed[/red]")
            parts.append(f"{passed_count} passed")
            parts.append(f"{total} total")
            console.print(f"Tests:       {', '.join(parts)}")
            
            console.print(f"Time:        {total_time:.2f}s")
    
    return 1 if failed_count > 0 else 0
