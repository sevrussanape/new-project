import os
import subprocess
import sys

def run_command(cmd, cwd=None):
    """Run a shell command and print output."""
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"Command failed: {cmd}")
    print(result.stdout)
    return result.stdout.strip()

def main():
    # Check if git is installed
    try:
        run_command("git --version")
    except:
        print("❌ Git is not installed or not in PATH. Please install Git first.")
        return

    # Check if we are in the project root (look for backend/ and frontend/)
    if not (os.path.isdir("backend") and os.path.isdir("frontend")):
        print("❌ Please run this script from the root of the project (where backend/ and frontend/ are located).")
        return

    # Create .gitignore if it doesn't exist
    gitignore_path = ".gitignore"
    if not os.path.exists(gitignore_path):
        print("📝 Creating .gitignore...")
        with open(gitignore_path, "w") as f:
            f.write("""# Python
__pycache__/
*.pyc
venv/
env/
*.egg-info/
dist/
build/
models/

# Node
node_modules/
npm-debug.log
yarn-debug.log
yarn-error.log
.env

# IDE / OS
.DS_Store
.vscode/
.idea/
*.swp
*.swo

# Build outputs
frontend/build/
frontend/.env.local
""")
    else:
        print("✅ .gitignore already exists.")

    # Check if already a Git repo
    if os.path.isdir(".git"):
        print("⚠️  Git repository already exists. Do you want to re-initialize? (y/N)")
        choice = input().strip().lower()
        if choice != 'y':
            print("Exiting.")
            return
        # Remove .git folder (careful!)
        import shutil
        shutil.rmtree(".git")
        print("Removed existing .git.")

    # Initialize Git
    print("🔧 Initializing Git repository...")
    run_command("git init")

    # Add all files
    print("📦 Adding files...")
    run_command("git add .")

    # Commit
    print("📝 Committing...")
    commit_message = "Initial commit: AI Stock Predictor dashboard"
    run_command(f'git commit -m "{commit_message}"')

    # Ask for remote URL
    print("\n📌 Enter your GitHub repository URL (e.g., https://github.com/username/repo.git or git@github.com:username/repo.git)")
    remote_url = input("URL: ").strip()
    if not remote_url:
        print("No URL provided. Exiting.")
        return

    # Set remote
    print("🔗 Setting remote...")
    run_command(f"git remote add origin {remote_url}")

    # Rename default branch to 'main' if needed
    current_branch = run_command("git rev-parse --abbrev-ref HEAD")
    if current_branch != "main":
        print("🔄 Renaming branch to 'main'...")
        run_command("git branch -M main")

    # Push
    print("🚀 Pushing to GitHub...")
    run_command("git push -u origin main")

    print("\n✅ Success! Your code is now on GitHub.")
    print(f"   View it at: {remote_url}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)