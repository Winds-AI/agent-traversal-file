# How to Publish Your First Release

This guide shows you **exactly** how to publish ATF Tools to GitHub, step by step.

---

## Prerequisites

1. **GitHub account** - Sign up at https://github.com if you don't have one
2. **Git installed** - Download from https://git-scm.com/
3. **Go installed** (optional) - Download from https://go.dev/dl/

---

## Step 1: Create GitHub Repository

### 1.1 Create New Repository

1. Go to https://github.com/new
2. Fill in:
   - **Repository name**: `atf` (or `atf-tools`)
   - **Description**: `Agent Traversable File - Self-indexing documents for AI agents`
   - **Public** (recommended) or Private
   - **Do NOT** initialize with README (we have our own)
3. Click **"Create repository"**

### 1.2 Note Your Repository URL

You'll see something like:
```
https://github.com/YOUR-USERNAME/atf.git
```

Keep this handy!

---

## Step 2: Upload Your Code

### 2.1 Open Terminal/Command Prompt

Navigate to the `repo` folder we created:

```bash
# Windows
cd S:\Random_stuff\Ideas\traversable-file\repo

# Mac/Linux
cd /path/to/traversable-file/repo
```

### 2.2 Initialize Git

```bash
git init
git add .
git commit -m "Initial commit: ATF Tools v1.0.0"
```

### 2.3 Connect to GitHub

Replace `YOUR-USERNAME` with your actual GitHub username:

```bash
git remote add origin https://github.com/YOUR-USERNAME/atf.git
git branch -M main
git push -u origin main
```

**You'll be asked for username and password:**
- Username: Your GitHub username
- Password: Use a [Personal Access Token](https://github.com/settings/tokens) (not your actual password)

---

## Step 3: Create Your First Release

### 3.1 Create a Git Tag

```bash
git tag v1.0.0
git push origin v1.0.0
```

### 3.2 Wait for GitHub Actions

1. Go to your repository on GitHub
2. Click **"Actions"** tab
3. You'll see "Build and Release" workflow running
4. Wait 2-5 minutes for it to complete

**What's happening:**
- GitHub is compiling your Go code for Windows, Mac, and Linux
- Creating binaries for each platform
- Uploading them to a new release

### 3.3 Check Your Release

1. Go to your repository
2. Click **"Releases"** (on the right side)
3. You should see **"v1.0.0"** with downloadable binaries!

**You now have:**
- ✅ `atf-windows-amd64.exe`
- ✅ `atf-darwin-amd64` (Mac Intel)
- ✅ `atf-darwin-arm64` (Mac Apple Silicon)
- ✅ `atf-linux-amd64`
- ✅ `atf-linux-arm64`
- ✅ `SHA256SUMS` (checksums)

---

## Step 4: Test the Installation

Try installing it yourself!

### Windows:

Open PowerShell and run:

```powershell
# Update install.ps1 with your username first!
irm https://raw.githubusercontent.com/YOUR-USERNAME/atf/main/install/install.ps1 | iex
```

### Mac/Linux:

Open Terminal and run:

```bash
# Update install.sh with your username first!
curl -fsSL https://raw.githubusercontent.com/YOUR-USERNAME/atf/main/install/install.sh | bash
```

### Test It Works:

```bash
atf --version
# Should show: ATF Tools v1.0.0

atf --help
# Should show usage information
```

---

## Step 5: Update README with Real Links

Edit `README.md` and replace placeholders:

**Find and replace:**
- `atf-tools/atf` → `YOUR-USERNAME/atf`
- Update all GitHub links to point to your repository

**Commit the changes:**

```bash
git add README.md
git commit -m "Update README with repository links"
git push
```

---

## Step 6: Share Your Project

Your project is now live! Share it:

**Direct download links:**
```
https://github.com/YOUR-USERNAME/atf/releases/latest
```

**Installation command:**
```bash
curl -fsSL https://raw.githubusercontent.com/YOUR-USERNAME/atf/main/install/install.sh | bash
```

**Repository:**
```
https://github.com/YOUR-USERNAME/atf
```

---

## Troubleshooting

### Issue: GitHub Actions Failed

**Check the logs:**
1. Go to "Actions" tab
2. Click the failed workflow
3. Read the error messages

**Common fixes:**
- Make sure `go/main.go` and `go/go.mod` are in the right folders
- Check that `.github/workflows/release.yml` is correctly formatted
- Ensure you pushed the tag: `git push origin v1.0.0`

### Issue: Binaries Not Created

**Make sure:**
- The workflow file is at `.github/workflows/release.yml`
- You pushed a tag starting with `v` (like `v1.0.0`)
- The workflow ran to completion (check Actions tab)

### Issue: Installation Script Doesn't Work

**Update the URLs in install scripts:**

Edit `install/install.sh` and `install/install.ps1`:
- Replace `atf-tools/atf` with `YOUR-USERNAME/atf`
- Commit and push changes

---

## Making Future Releases

### When you make changes:

```bash
# 1. Make your changes to code
# 2. Commit them
git add .
git commit -m "Add new feature"
git push

# 3. Create new version tag
git tag v1.1.0
git push origin v1.1.0

# 4. GitHub Actions automatically builds and releases!
```

---

## What You've Accomplished

✅ Created a GitHub repository  
✅ Published your code  
✅ Set up automatic builds for all platforms  
✅ Created downloadable binaries  
✅ Made installation scripts  
✅ Shared your project with the world  

**Congratulations! You're now maintaining an open-source project!** 🎉

---

## Next Steps

1. **Add more examples** - Create more `.atf` files in `examples/`
2. **Write documentation** - Add to `docs/` folder
3. **Fix bugs** - Users will report issues on GitHub
4. **Add features** - Implement new commands or improvements
5. **Get contributors** - Others can help improve the project!

---

## Questions?

- **How do I delete a release?**  
  Go to Releases → Click the release → Delete

- **How do I update a release?**  
  Create a new tag (e.g., `v1.0.1`) and push it

- **Can I test without creating a real release?**  
  Yes! Use `workflow_dispatch` - go to Actions tab and click "Run workflow"

- **How do I make the repository private?**  
  Settings → Danger Zone → Change visibility

---

## Summary Commands

```bash
# Initial setup
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR-USERNAME/atf.git
git push -u origin main

# Create release
git tag v1.0.0
git push origin v1.0.0

# Future updates
git add .
git commit -m "Your changes"
git push
git tag v1.1.0
git push origin v1.1.0
```

**That's it! You're published!** 🚀
