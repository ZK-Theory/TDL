# ParaView+TTK Bundle Installation Instructions

## Installation Steps

### Option 1: Silent Installation (Recommended)
Run the installer silently with default settings:

```powershell
# From PowerShell (Run as Administrator)
cd C:\Projects\TDL\docs\ttk_installers
.\ttk-paraview-v5.13.0.exe /S /D=C:\Program Files\ParaView-TTK-5.13.0
```

### Option 2: GUI Installation
1. Double-click `ttk-paraview-v5.13.0.exe`
2. Follow the installation wizard
3. **Important:** Install to a location like `C:\Program Files\ParaView-TTK-5.13.0`
4. Do NOT overwrite existing ParaView 6.0.1 installation

## Post-Installation Verification

After installation, verify TTK is available:

```bash
# Test pvpython with TTK
"/c/Program Files/ParaView-TTK-5.13.0/bin/pvpython.exe" -c "from paraview.simple import TTKPersistenceDiagram; print('TTK available in ParaView!')"
```

## Environment Configuration

Add to your project's environment variables or shell configuration:

```bash
# Bash/Git Bash
export PARAVIEW_TTK_BIN="/c/Program Files/ParaView-TTK-5.13.0/bin"
export PVPYTHON="$PARAVIEW_TTK_BIN/pvpython.exe"

# PowerShell
$env:PARAVIEW_TTK_BIN = "C:\Program Files\ParaView-TTK-5.13.0\bin"
$env:PVPYTHON = "$env:PARAVIEW_TTK_BIN\pvpython.exe"
```

## What Gets Installed

- **ParaView 5.13.0** with TTK 1.3.0 pre-integrated
- **TTK filters** for topological data analysis
- **pvpython** for ParaView scripting with TTK
- **VTK 9.3.x** bundled with ParaView (isolated from project VTK 9.5.2)

## Notes

- This installation is **separate** from your existing ParaView 6.0.1
- ParaView 5.13.0 has VTK 9.3.x, which is different from project VTK 9.5.2
- Use conda `ttk_env` for Python API access (VTK 9.3.x)
- Use this ParaView installation for TTK visualization scripts
