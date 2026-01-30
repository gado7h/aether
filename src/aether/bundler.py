"""
Aether - Script bundler for Roblox Cloud execution
"""
from pathlib import Path

import sys
import os

# Get the package's testez directory
# Support PyInstaller's _MEIPASS for bundled data
if hasattr(sys, '_MEIPASS'):
    PACKAGE_DIR = Path(sys._MEIPASS) / "aether"
else:
    PACKAGE_DIR = Path(__file__).parent

TESTEZ_DIR = PACKAGE_DIR / "vendor" / "testez"


def bundle_testez():
    """Bundle TestEZ framework from internal package directory"""
    bundle = []
    
    if not TESTEZ_DIR.exists():
        raise FileNotFoundError(f"TestEZ not found at {TESTEZ_DIR}")
    
    # Create TestEZ folder structure - testez module first, then children
    bundle.append("""
-- Bundle TestEZ framework
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TestEZFolder = Instance.new("Folder")
TestEZFolder.Name = "TestEZ"
TestEZFolder.Parent = ReplicatedStorage

-- Create main testez ModuleScript first
local testezModule = Instance.new("ModuleScript")
testezModule.Name = "testez"
testezModule.Parent = TestEZFolder

-- Create Reporters folder as child of testez module
local ReportersFolder = Instance.new("Folder")
ReportersFolder.Name = "Reporters"
ReportersFolder.Parent = testezModule
""")
    
    # Read init.lua content first
    init_path = TESTEZ_DIR / "init.lua"
    if init_path.exists():
        with open(init_path, "r", encoding="utf-8") as f:
            init_content = f.read()
        bundle.append(f"""
do
    _G.VirtualFiles = _G.VirtualFiles or {{}}
    _G.VirtualFiles[testezModule] = function()
        local script = testezModule
        {init_content}
    end
end
""")
    
    # Map TestEZ child files (all become children of testezModule)
    testez_child_files = {
        "Context": TESTEZ_DIR / "Context.lua",
        "Expectation": TESTEZ_DIR / "Expectation.lua",
        "ExpectationContext": TESTEZ_DIR / "ExpectationContext.lua",
        "LifecycleHooks": TESTEZ_DIR / "LifecycleHooks.lua",
        "TestBootstrap": TESTEZ_DIR / "TestBootstrap.lua",
        "TestEnum": TESTEZ_DIR / "TestEnum.lua",
        "TestNode": TESTEZ_DIR / "TestNode.lua",
        "TestPlan": TESTEZ_DIR / "TestPlan.lua",
        "TestPlanner": TESTEZ_DIR / "TestPlanner.lua",
        "TestResults": TESTEZ_DIR / "TestResults.lua",
        "TestRunner": TESTEZ_DIR / "TestRunner.lua",
        "TestSession": TESTEZ_DIR / "TestSession.lua",
    }
    
    reporter_files = {
        "TextReporter": TESTEZ_DIR / "Reporters" / "TextReporter.lua",
        "TextReporterQuiet": TESTEZ_DIR / "Reporters" / "TextReporterQuiet.lua",
        "TeamCityReporter": TESTEZ_DIR / "Reporters" / "TeamCityReporter.lua",
    }
    
    # Bundle child TestEZ files as children of testezModule
    for name, file_path in testez_child_files.items():
        if not file_path.exists():
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        bundle.append(f"""
do
    local scriptInstance = Instance.new("ModuleScript")
    scriptInstance.Name = "{name}"
    scriptInstance.Parent = testezModule
    
    _G.VirtualFiles = _G.VirtualFiles or {{}}
    _G.VirtualFiles[scriptInstance] = function()
        local script = scriptInstance
        {content}
    end
end
""")
    
    # Bundle reporter files as children of ReportersFolder
    for name, file_path in reporter_files.items():
        if not file_path.exists():
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        bundle.append(f"""
do
    local scriptInstance = Instance.new("ModuleScript")
    scriptInstance.Name = "{name}"
    scriptInstance.Parent = ReportersFolder
    
    _G.VirtualFiles = _G.VirtualFiles or {{}}
    _G.VirtualFiles[scriptInstance] = function()
        local script = scriptInstance
        {content}
    end
end
""")
    
    return "\n".join(bundle)

def get_roblox_path(file_path, root_dir):
    """
    Maps file system path to Roblox instance path components.
    Returns (Service, [ParentFolders...], Name, ClassName)
    """
    rel_path = file_path.relative_to(root_dir)
    parts = list(rel_path.parts)
    
    if parts[0] == "src":
        root_map = {
            "server": "ServerScriptService",
            "client": "StarterPlayer",
            "shared": "ReplicatedStorage"
        }
        
        if len(parts) < 3:
            return None
        
        service_folder = parts[1]
        service_name = root_map.get(service_folder, "ServerScriptService")
        remaining = parts[2:]
        
        filename = remaining[-1]
        script_name = filename.split(".")[0]
        
        # Check for init files OR files that match their parent folder name (Rojo style)
        is_init = filename in ("init.luau", "init.server.luau", "init.client.luau")
        if not is_init and len(remaining) > 1 and script_name == remaining[-2]:
             is_init = True
             
        class_name = "ModuleScript"
        
        if filename.endswith(".server.luau"):
            class_name = "Script"
        elif filename.endswith(".client.luau"):
            class_name = "LocalScript"
            
        if is_init:
            script_name = remaining[-2] if len(remaining) > 1 else "Unknown"
            parent_folders = remaining[:-2]
        else:
            parent_folders = remaining[:-1]
            
        if service_folder == "shared":
            parent_folders = ["Shared"] + list(parent_folders)
             
        if service_folder == "client":
            service_name = "StarterPlayer"
            parent_folders = ["StarterPlayerScripts"] + list(parent_folders)

        return (service_name, parent_folders, script_name, class_name)

    elif parts[0] == "Packages":
        service_name = "ReplicatedStorage"
        parent_folders = ["Packages"] + list(parts[1:-1])
        
        filename = parts[-1]
        script_name = filename.split(".")[0]
        class_name = "ModuleScript"
        
        # Check for init files OR files that match their parent folder name
        is_init = filename in ("init.lua", "init.luau")
        if not is_init and len(parts) > 2 and script_name == parts[-2]:
             is_init = True
        
        if is_init:
            script_name = parts[-2]
            parent_folders = ["Packages"] + list(parts[1:-2])
             
        return (service_name, parent_folders, script_name, class_name)
        
    return None



from .rojo_resolver import RojoResolver

def bundle_scripts(paths, config):
    """Bundle all source code into a Lua script using Rojo sourcemap"""
    bundle = []
    source_map = [] # List of (start_line, end_line, file_path, original_start_line)
    current_line = 1
    
    def append_chunk(chunk, path=None, content_offset=0, original_start=1):
        nonlocal current_line
        bundle.append(chunk)
        
        # Calculate lines in this chunk
        # We use split('\n') to mimic how it will be joined or written
        num_lines = chunk.count('\n') + 1
        
        if path:
            # Map the content part of the chunk
            # content_offset is the number of lines BEFORE the content starts in this chunk
            start = current_line + content_offset
            # The content length is... we need to know the content length inside the chunk?
            # It's tricky because we only have the full chunk here.
            # But the caller knows.
            pass
            
        current_line += num_lines # +1 for the join newline happens implicitly if we treat each list item as having its own lines? 
        # Actually "\n".join(bundle) inserts newlines.
        # If chunk is "A", it's 1 line. Next chunk starts on line 2.
        # So current_line increment is correct.
        
    # Helper to append and track
    # We will compute offsets manually in the loop
    
    chunk = "print('--- Bundling Game Source (Rojo) ---')"
    bundle.append(chunk)
    current_line += chunk.count('\n') + 1
    
    # Helper for creating folders
    chunk = """
local function GetOrCreate(parent, name)
    local existing = parent:FindFirstChild(name)
    if existing then return existing end
    local folder = Instance.new("Folder")
    folder.Name = name
    folder.Parent = parent
    return folder
end
"""
    bundle.append(chunk)
    current_line += chunk.count('\n') + 1

    
    print("Resolving Rojo sourcemap...")
    rojo_project = config.get("rojo_project", "default.project.json")
    resolver = RojoResolver(rojo_project)
    
    if not resolver.generate_sourcemap():
        print(f"[WARN] Could not generate Rojo sourcemap (checked {rojo_project} and sourcemap.json)")
        print("       Falling back to default file system scan (src/ -> ServerScriptService, etc.)")
        return bundle_scripts_fallback(paths)
        
    print("Bundling scripts...")
    
    files_to_process = resolver.get_all_scripts()
    
    # Sort for deterministic bundle order
    files_to_process.sort(key=lambda p: str(p))
    
    for path in files_to_process:
        # Get (Service, [Folders], ScriptName, ClassName) implies we need ClassName in resolver?
        # Resolver currently returns list of path components [Service, Folder, Script]
        # We need to infer class name from extension or filename still?
        # The sourcemap JSON has "className". RojoResolver should ideally return it.
        # But _build_mappings in RojoResolver didn't store className.
        # Let's assume RojoResolver needs an update or we infer here.
        # Infereference from file path extension (.server.luau etc) is standard Rojo behavior.
        
        path_components = resolver.get_roblox_path(path)
        if not path_components:
            continue
            
        service_name = path_components[0]
        remaining = path_components[1:]
        
        # Last component is method (script) name, parents are folders
        script_name = remaining[-1]
        folders = remaining[:-1]
        
        # Determine class name based on file extension
        # (This is a simplification; ideally use sourcemap 'className' if available)
        fname = path.name
        class_name = "ModuleScript"
        is_json = fname.lower().endswith(".json")
        
        if fname.endswith(".server.luau") or fname.endswith(".server.lua"):
             class_name = "Script"
        elif fname.endswith(".client.luau") or fname.endswith(".client.lua"):
             class_name = "LocalScript"
             
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if is_json:
                # Wrap JSON content in JSONDecode to return as a table (ModuleScript behavior)
                # Find safe Lua string delimiter
                level = 0
                while True:
                    eq = "=" * level
                    close_seq = f"]{eq}]"
                    if close_seq not in content:
                        start_delim = f"[{eq}["
                        end_delim = close_seq
                        break
                    level += 1
                
                content = f"return game:GetService('HttpService'):JSONDecode({start_delim}{content}{end_delim})"

        except Exception as e:
            print(f"Skipping {path}: {e}")
            continue

        # Prepare the preamble (lines before content)
        preamble = f"""
do
    local current = game:GetService("{service_name}")
"""
        for folder in folders:
            preamble += f'    current = GetOrCreate(current, "{folder}")\n'
            
        preamble += f"""
    local scriptInstance = current:FindFirstChild("{script_name}")
    if not scriptInstance then
        scriptInstance = Instance.new("{class_name}")
        scriptInstance.Name = "{script_name}"
        scriptInstance.Parent = current
    end
    
    _G.VirtualFiles = _G.VirtualFiles or {{}}
    _G.VirtualFiles[scriptInstance] = function(...) 
        local script = scriptInstance 
"""
        # Note: The preamble ends with a newline in the triple-quote string?
        # Yes, standard python triple-quote behavior.
        # The content comes next.
        
        chunk = preamble + f"        {content}\n    end\nend\n"
        
        # Calculate mapping
        # Count lines in preamble
        # We need accurate count. strip() might be dangerous if indentation matters for counting
        preamble_lines = preamble.count('\n')
        # Check if preamble ends with newline... yes it does.
        
        # The content starts at current_line + preamble_lines
        start_map = current_line + preamble_lines
        content_lines_count = content.count('\n') + 1
        end_map = start_map + content_lines_count - 1
        
        source_map.append({
            "file": str(path),
            "start": start_map,
            "end": end_map,
            "original_start": 1
        })
        
        bundle.append(chunk)
        current_line += chunk.count('\n') + 1


    # Require shim
    shim = """
local _oldRequire = require
_G.LoadedModules = {}

function require(module)
    if module == nil then
        error("REQUIRE_NIL_ERROR: require called with nil")
    end
    -- print("REQUIRE CALL: " .. tostring(module))
    if typeof(module) == "Instance" then
        if not module:IsA("ModuleScript") then
             error("REQUIRE_INSTANCE_ERROR: " .. module.ClassName .. " " .. module:GetFullName())
        end
        
        if _G.LoadedModules[module] then
            return _G.LoadedModules[module]
        end
        if _G.VirtualFiles and _G.VirtualFiles[module] then
             local res = _G.VirtualFiles[module]()
             _G.LoadedModules[module] = res
             return res
        end
        error("REQUIRE_MISSING_VIRTUAL: " .. module:GetFullName()) 
    end
    error("REQUIRE_INVALID_TYPE: " .. typeof(module) .. " " .. tostring(module))
end
"""
    bundle.append(shim)
    
    return "\n".join(bundle), source_map



def bundle_scripts_fallback(paths):
    """Legacy bundling logic (fallback)"""
    bundle = []
    source_map = []
    current_line = 1
    
    chunk = "print('--- Bundling Game Source (Legacy Fallback) ---')"
    bundle.append(chunk)
    current_line += chunk.count('\n') + 1
    
    # Helper for creating folders
    chunk = """
local function GetOrCreate(parent, name)
    local existing = parent:FindFirstChild(name)
    if existing then return existing end
    local folder = Instance.new("Folder")
    folder.Name = name
    folder.Parent = parent
    return folder
end
"""
    bundle.append(chunk)
    current_line += chunk.count('\n') + 1

    
    src_files = list(paths["src"].rglob("*.luau"))
    pkg_files = list(paths["packages"].rglob("*.lua")) + list(paths["packages"].rglob("*.luau"))
    files_to_process = src_files + pkg_files
    
    def sort_key(p):
        is_init = p.name in ('init.lua', 'init.luau')
        return (len(p.parts), 0 if is_init else 1, str(p))
    
    files_to_process.sort(key=sort_key)
    
    for path in files_to_process:
        info = get_roblox_path(path, paths["root"])
        if not info:
            continue
        
        service_name, folders, script_name, instance_type = info
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except:
            continue

        # Prepare preamble
        preamble = f"""
do
    local current = game:GetService("{service_name}")
"""
        for folder in folders:
            preamble += f'    current = GetOrCreate(current, "{folder}")\n'
            
        preamble += f"""
    local scriptInstance = current:FindFirstChild("{script_name}")
    if not scriptInstance then
        scriptInstance = Instance.new("{instance_type}")
        scriptInstance.Name = "{script_name}"
        scriptInstance.Parent = current
    end
    
    _G.VirtualFiles = _G.VirtualFiles or {{}}
    _G.VirtualFiles[scriptInstance] = function(...) 
        local script = scriptInstance 
"""
        chunk = preamble + f"        {content}\n    end\nend\n"
        
        preamble_lines = preamble.count('\n')
        start_map = current_line + preamble_lines
        content_lines_count = content.count('\n') + 1
        end_map = start_map + content_lines_count - 1
        
        source_map.append({
            "file": str(path),
            "start": start_map,
            "end": end_map,
            "original_start": 1
        })
        
        bundle.append(chunk)
        current_line += chunk.count('\n') + 1


    # Require shim logic repeated or shared...
    # For brevity, I'll rely on the main bundle_scripts to append the shim if fallback is used?
    # No, fallback needs to be self-contained or we structure it better.
    # Let's copy the shim for now to be safe.
    # Require shim
    shim = """
local _oldRequire = require
_G.LoadedModules = {}

function require(module)
    if module == nil then
        error("REQUIRE_NIL_ERROR: require called with nil")
    end
    if typeof(module) == "Instance" then
        if not module:IsA("ModuleScript") then
             error("REQUIRE_INSTANCE_ERROR: " .. module.ClassName .. " " .. module:GetFullName())
        end
        if _G.LoadedModules[module] then return _G.LoadedModules[module] end
        if _G.VirtualFiles and _G.VirtualFiles[module] then
             local res = _G.VirtualFiles[module]()
             _G.LoadedModules[module] = res
             return res
        end
        error("REQUIRE_MISSING_VIRTUAL: " .. module:GetFullName()) 
    end
    error("REQUIRE_INVALID_TYPE: " .. typeof(module) .. " " .. tostring(module))
end
"""
    bundle.append(shim)
    
    return "\n".join(bundle), source_map



def get_testez_driver(spec_path, tests_dir):
    """Generate TestEZ driver for a spec file"""
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_content = f.read()
    
    # Load helpers if exists
    helpers_path = tests_dir / "_helpers.luau"
    if helpers_path.exists():
        with open(helpers_path, "r", encoding="utf-8") as f:
            helpers_content = f.read()
    else:
        helpers_content = "return {}"
    
    # Build driver using string concatenation to avoid f-string brace issues
    driver = []
    driver.append("""
-- --- TEST RUNNER (TestEZ) ---
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TestEZ = require(ReplicatedStorage.TestEZ.testez)

print("--- Starting TestEZ Bootstrap ---")

-- Create mock tests folder structure
local TestsFolder = Instance.new("Folder")
TestsFolder.Name = "Tests"
TestsFolder.Parent = ReplicatedStorage

-- Create helpers module
local HelpersModule = Instance.new("ModuleScript")
HelpersModule.Name = "_helpers"
HelpersModule.Parent = TestsFolder

_G.VirtualFiles = _G.VirtualFiles or {}
_G.VirtualFiles[HelpersModule] = function()
    local script = HelpersModule
""")
    driver.append(helpers_content)
    driver.append("""
end

-- Create spec module
local SpecModule = Instance.new("ModuleScript")
""")
    driver.append(f'SpecModule.Name = "{spec_path.stem}"')
    driver.append("""
SpecModule.Parent = TestsFolder

-- Mount the spec file function directly
local testMethod = (function()
    local script = SpecModule
""")
    # Calculate the offset of the spec content within the driver
    # Count lines in the driver so far (before appending spec_content)
    pre_spec_lines = sum(chunk.count('\n') for chunk in driver) + len(driver) - 1  # account for join newlines
    spec_offset = pre_spec_lines + 1  # +1 because next line is where spec starts
    
    driver.append(spec_content)
    spec_len = spec_content.count('\n') + 1
    
    driver.append("""
end)()

-- Use TestEZ internals directly instead of going through module discovery
local TestPlanner = TestEZ.TestPlanner
local TestRunner = TestEZ.TestRunner

local modules = {
    {
        method = testMethod,
        path = {"TestSpec"},
        pathStringForSorting = "testspec"
    }
}

local plan = TestPlanner.createPlan(modules, nil, {})
local results = TestRunner.runPlan(plan)

-- Helper to collect granular results
local function collectResults(node, list)
    list = list or {}
    
    if node.planNode and node.planNode.type == "It" then
        local status = "Unknown"
        if node.status == "Success" then status = "Success" end
        if node.status == "Failure" then status = "Failure" end
        if node.status == "Skipped" then status = "Skipped" end
        
        table.insert(list, {
            name = node.planNode.phrase,
            status = status,
            errors = node.errors
        })
    end
    
    if node.children then
        for _, child in ipairs(node.children) do
            collectResults(child, list)
        end
    end
    
    return list
end

local flatResults = collectResults(results)

local status = "Success"
if results.failureCount > 0 then
    status = "FAILED"
end

-- Return complete test information
return {
    status = status,
    results = flatResults,
    failures = results.errors,
    failureCount = results.failureCount
}
""")
    return "\n".join(driver), spec_offset, spec_len

