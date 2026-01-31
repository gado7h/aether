"""
Aether - Professional CLI UI using Rich
"""
import os
import sys
import time
import threading
from pathlib import Path

from rich.console import Console

# Initialize console with highlight=False to prevent auto-coloring numbers/paths
# force_terminal=True ensures colors work even if pipped
console = Console(highlight=False, force_terminal=True)

# Simple spinner (classic)
SPINNER_FRAMES = ["-", "\\", "|", "/"]


class Dashboard:
    """Professional CLI dashboard for Aether watch mode"""
    
    def __init__(self, version="0.4.0"):
        self.version = version
        self.workspace = os.getcwd()
        self.rojo_project = "default.project.json"
        self._spinner_thread = None
        self._spinner_running = False
        self._current_file = None
        self._progress = 0
        
    def clear(self):
        """Clear the terminal screen"""
        console.clear()
            
    def print_header(self):
        """Print the Aether header (minimal, no emojis)"""
        console.print(f"Aether v{self.version}")
        console.print(f"Workspace: {os.path.basename(self.workspace)}")
        # console.print(f"Rojo Project: {self.rojo_project}") # Removing to reduce noise
        console.print()
            
    def _spinner_loop(self):
        """Animate spinner while waiting for cloud response"""
        frame_idx = 0
        while self._spinner_running:
            frame = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
            
            # Use dim text for progress
            status = f"\r{frame} Running tests... {int(self._progress)}%"
            # Simple output, no fancy bar to keep it minimal as requested? 
            # User example: "Running: tests/raycast.spec.luau ..."
            # But they also asked for "Muted" style.
            # Let's keep it simple.
            
            print(f"\r{status}".ljust(80), end="", flush=True)
            
            frame_idx += 1
            time.sleep(0.08)
            
            # Simulate progress 
            if self._progress < 90:
                self._progress += 0.5
                
    def start_spinner(self, filename):
        """Start the spinner animation"""
        self._current_file = filename
        self._progress = 0
        self._spinner_running = True
        self._spinner_thread = threading.Thread(target=self._spinner_loop, daemon=True)
        self._spinner_thread.start()
        
    def stop_spinner(self):
        """Stop the spinner animation"""
        self._spinner_running = False
        if self._spinner_thread:
            self._spinner_thread.join(timeout=0.5)
        print("\r" + " " * 80 + "\r", end="")  # Clear the line
        
    def print_running(self, filename):
        """Print the running status"""
        # Minimalist running message
        pass # We use spinner for this now
        
    def print_result(self, name, status, duration=0, error=None, traceback=None):
        """Print a single test result with minimalist styling"""
        # Note: formatting depends on context, but here we print individual tests
        if status in ("PASS", "PASSED"):
            # PASS  <name> (<duration>)
            if duration > 0:
                console.print(f"[bold green]PASS[/bold green]  {name} [dim]({duration:.2f}s)[/dim]")
            else:
                console.print(f"[bold green]PASS[/bold green]  {name}")
        elif status in ("FAIL", "FAILED"):
            # FAIL  <name>
            #       <error>
            #       at <traceback>
            console.print(f"[bold red]FAIL[/bold red]  {name}")
            if error:
                console.print(f"      {error}")
            if traceback:
                # console.print() # No extra newline
                # Clean up traceback label? User asked to "Remove unnecessary prefixes"
                # "at tests/failing.spec.luau:5"
                for line in traceback.split("\n"):
                    if line.strip():
                        # Try to format as "at <path>"
                        # If the line is just a path, prefix with "at "
                        clean_line = line.strip()
                        if not clean_line.startswith("at "):
                             console.print(f"      [dim]at {clean_line}[/dim]")
                        else:
                             console.print(f"      [dim]{clean_line}[/dim]")
        else:
            # Show actual status text if unknown, or SKIP
            badge = status if status else "SKIP"
            console.print(f"[bold yellow]{badge}[/bold yellow]  {name}")
                
    def print_summary(self, files_passed, files_failed, files_total, 
                      tests_passed, tests_failed, tests_total, duration):
        """Print the summary section"""
        console.print()
        console.print("-" * 60, style="dim") # Separation line
        
        # Test Files line
        parts = []
        if files_failed > 0:
            parts.append(f"[red]{files_failed} failed[/red]")
        parts.append(f"{files_passed} passed")
        parts.append(f"{files_total} total")
        console.print(f"Test Files:  {', '.join(parts)}")
        
        # Tests line    
        parts = []
        if tests_failed > 0:
            parts.append(f"[red]{tests_failed} failed[/red]")
        parts.append(f"{tests_passed} passed")
        parts.append(f"{tests_total} total")
        console.print(f"Tests:       {', '.join(parts)}")
            
        console.print(f"Time:        {duration:.2f}s")
            
    def print_watching(self):
        """Print the watching status and key bindings"""
        console.print()
        console.print("[dim]Watching for file changes... \\[f/a/q/enter][/dim]")


def get_key_press():
    """Get a single key press (cross-platform)"""
    try:
        if sys.platform == 'win32':
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\r':
                    return 'enter'
                return key.decode('utf-8', errors='ignore').lower()
        else:
            import select
            import tty
            import termios
            
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                if select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1)
                    if key == '\n':
                        return 'enter'
                    return key.lower()
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    except:
        pass
    return None
