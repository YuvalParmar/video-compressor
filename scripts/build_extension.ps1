$ErrorActionPreference = "Stop"

python -m pip install --upgrade pybind11
cmake -S . -B build -A x64
cmake --build build --config Release
$module = Get-ChildItem -Path build -Recurse -Filter "semantic_codec*.pyd" | Select-Object -First 1
if (-not $module) {
    throw "CMake completed but semantic_codec.pyd was not found."
}
Copy-Item $module.FullName -Destination .
Write-Host "Built $($module.Name)"
