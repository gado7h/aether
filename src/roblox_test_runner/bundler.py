"""
Roblox Test Runner - Script bundler for Roblox Cloud execution
"""
from pathlib import Path

import sys
import os

# Get the package's testez directory
# Support PyInstaller's _MEIPASS for bundled data
if hasattr(sys, '_MEIPASS'):
    PACKAGE_DIR = Path(sys._MEIPASS) / "roblox_test_runner"
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


def bundle_scripts(paths):
    """Bundle all source code and packages into a Lua script"""
    bundle = []
    bundle.append("print('--- Bundling Game Source & Packages ---')")
    
    # Helper for creating folders
    bundle.append("""
local function GetOrCreate(parent, name)
    local existing = parent:FindFirstChild(name)
    if existing then return existing end
    local folder = Instance.new("Folder")
    folder.Name = name
    folder.Parent = parent
    return folder
end
""")
    
    print("Bundling scripts...")
    
    src_files = list(paths["src"].rglob("*.luau"))
    pkg_files = list(paths["packages"].rglob("*.lua")) + list(paths["packages"].rglob("*.luau"))
    files_to_process = src_files + pkg_files
    
    def sort_key(p):
        # Sort by depth first, then by whether it's an init file (init first), then name
        is_init = p.name in ('init.lua', 'init.luau')
        # We want init files to come before other files in same directory, content-wise
        # But also parents before children.
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
        except Exception as e:
            print(f"Skipping {path}: {e}")
            continue

        chunk = f"""
do
    local current = game:GetService("{service_name}")
"""
        for folder in folders:
            chunk += f'    current = GetOrCreate(current, "{folder}")\n'
            
        chunk += f"""
    local scriptInstance = current:FindFirstChild("{script_name}")
    if not scriptInstance then
        scriptInstance = Instance.new("{instance_type}")
        scriptInstance.Name = "{script_name}"
        scriptInstance.Parent = current
    end
    
    _G.VirtualFiles = _G.VirtualFiles or {{}}
    _G.VirtualFiles[scriptInstance] = function(...) 
        local script = scriptInstance 
        {content}
    end
end
"""
        bundle.append(chunk)

    # Require shim
    bundle.append("""
local _oldRequire = require
_G.LoadedModules = {}

function require(module)
    if module == nil then
        error("REQUIRE_NIL_ERROR: require called with nil")
    end
    print("REQUIRE CALL: " .. tostring(module))
    if typeof(module) == "Instance" then
        print("  Type: Instance (" .. module.ClassName .. ") FullName: " .. module:GetFullName())
        if not module:IsA("ModuleScript") then
             -- print("  [ERROR] Require called on non-ModuleScript: " .. module.ClassName)
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
""")
    return "\n".join(bundle)


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
    driver.append(spec_content)
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
    
    if node.planNode and node.planNode.type == "it" then
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
    return "\n".join(driver)
