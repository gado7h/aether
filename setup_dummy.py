import os
from pathlib import Path

def setup_dummy_project():
    root = Path("c:/Users/Majhool/Documents/aether/testing_workspace/dummy_project")
    if root.exists():
        import shutil
        shutil.rmtree(root)
    
    root.mkdir(parents=True)
    (root / "src/server").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    
    # math.luau
    with open(root / "src/server/math.luau", "w") as f:
        f.write("""
local Math = {}
function Math.add(a, b)
    return a + b
end
return Math
""")

    # math.spec.luau
    with open(root / "tests/math.spec.luau", "w") as f:
        f.write("""
return function()
    local Math = require(game:GetService("ServerScriptService").math)
    
    describe("Math", function()
        it("should add numbers", function()
            expect(Math.add(1, 2)).to.equal(3)
        end)
    end)
end
""")

    # failing.spec.luau
    with open(root / "tests/failing.spec.luau", "w") as f:
        f.write("""
return function()
    describe("Failing", function()
        it("should fail intentionally", function()
            expect(1).to.equal(2)
        end)
    end)
end
""")
    
    # Config
    with open(root / "aether.toml", "w") as f:
        f.write("""
[project]
name = "dummy"
version = "0.1.0"
""")

    print(f"Created dummy project at {root}")

if __name__ == "__main__":
    setup_dummy_project()
