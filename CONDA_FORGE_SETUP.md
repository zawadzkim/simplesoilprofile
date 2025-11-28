# Adding conda-forge Publishing to simplesoilprofile

This guide shows how to enable automated conda-forge publishing using the reusable workflow.

## What You Get

After setup, every time you release a new version:

1. ✅ **PyPI**: Published automatically as before
2. ✅ **conda-forge**: Automatic PR created to update the feedstock
3. ✅ **Documentation**: Deployed to GitHub Pages
4. ✅ **GitHub Release**: Created with release notes

## Setup Steps

### 1. Enable conda-forge in Workflow ✅ DONE

Your `cd.yaml` has been updated with just 3 new parameters:

```yaml
publish-conda-forge: true
conda-forge-feedstock: 'simplesoilprofile-feedstock'
conda-forge-branch: 'auto-update'
```

### 2. Create conda-forge Feedstock (One-time setup)

**Option A: Submit to staged-recipes (Recommended)**

1. Fork [conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes)
2. Copy `conda-recipe/meta.yaml` to `recipes/simplesoilprofile/meta.yaml`
3. Update the SHA256 hash with the real value from PyPI
4. Submit PR to staged-recipes
5. Once merged, your feedstock will be created automatically

**Option B: Manual feedstock creation**

If you have conda-forge permissions, you can create the feedstock directly.

### 3. Configure GitHub Secrets

Add to your repository secrets:

```
CONDA_FORGE_TOKEN = your_github_token_with_conda_forge_access
```

Or use the default `GITHUB_TOKEN` (may have limited access).

### 4. Update Package Dependencies

Make sure your `pyproject.toml` dependencies match what's available on conda-forge:

```toml
dependencies = [
    "pydantic>=2.0",
    "matplotlib",
    "pandas", 
    "numpy",
    "rosetta-soil"  # Check if available on conda-forge
]
```

## How It Works

When you push to `main`:

1. **Version Check**: Checks if version tag already exists
2. **Testing**: Runs full test suite
3. **PyPI Publishing**: Publishes to PyPI first
4. **conda-forge Update**: 
   - Fetches package info from PyPI
   - Creates branch in feedstock repo
   - Updates `meta.yaml` with new version and SHA256
   - Creates pull request automatically
5. **Documentation**: Deploys docs to GitHub Pages

## Example Workflow Run

```bash
# 1. You release v0.2.0
git tag v0.2.0
git push origin v0.2.0

# 2. Workflow runs automatically:
#    ✅ Tests pass
#    ✅ PyPI: simplesoilprofile-0.2.0 published
#    ✅ conda-forge: PR created at conda-forge/simplesoilprofile-feedstock
#    ✅ Docs: https://zawadzkim.github.io/simplesoilprofile updated

# 3. conda-forge maintainers merge the PR
# 4. Users can install with: conda install -c conda-forge simplesoilprofile
```

## Benefits

- **Zero manual work**: Everything automated after initial setup
- **Scientific ecosystem**: Better reach in research community  
- **Dependency management**: conda handles complex scientific dependencies
- **Cross-platform**: Consistent installation across OS
- **Environment isolation**: Works seamlessly with conda environments

## Next Steps

1. **Create the feedstock** via staged-recipes submission
2. **Test the workflow** with a new version
3. **Update documentation** to mention conda-forge installation option

The workflow is ready to go - just need the conda-forge feedstock setup! 🚀