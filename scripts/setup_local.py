"""
Setup script for local development environment
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command"""
    print(f"\n📦 {description}...")
    print(f"   Command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   ❌ Error: {result.stderr}")
        return False
    print(f"   ✅ Success")
    return True


def check_docker():
    """Check if Docker is running"""
    print("\n🔍 Checking Docker...")
    result = subprocess.run("docker ps", shell=True, capture_output=True)
    if result.returncode != 0:
        print("   ❌ Docker is not running. Please start Docker Desktop first.")
        return False
    print("   ✅ Docker is running")
    return True


def setup_venv():
    """Setup virtual environment"""
    print("\n🐍 Setting up Python virtual environment...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("   ℹ️  Virtual environment already exists")
        return True
    
    return run_command(
        f"{sys.executable} -m venv venv",
        "Creating virtual environment"
    )


def install_deps():
    """Install dependencies"""
    print("\n📥 Installing dependencies...")
    
    # Determine pip path
    if os.name == "nt":  # Windows
        pip_path = "venv\\Scripts\\pip"
    else:
        pip_path = "venv/bin/pip"
    
    return run_command(
        f"{pip_path} install -r requirements-v3.txt",
        "Installing Python packages"
    )


def start_services():
    """Start Docker services"""
    print("\n🐳 Starting local services (Redis, Qdrant)...")
    return run_command(
        "docker-compose up -d",
        "Starting Docker containers"
    )


def check_env():
    """Check environment file"""
    print("\n🔐 Checking environment configuration...")
    
    env_path = Path(".env")
    env_example = Path(".env.example")
    
    if not env_path.exists():
        if env_example.exists():
            print("   ⚠️  .env file not found. Copying from .env.example...")
            with open(env_example, 'r') as f:
                content = f.read()
            with open(env_path, 'w') as f:
                f.write(content)
            print("   ✅ Created .env file")
            print("   ⚠️  Please edit .env and add your API keys!")
        else:
            print("   ❌ .env.example not found!")
            return False
    else:
        print("   ✅ .env file exists")
    
    # Check for required keys
    with open(env_path, 'r') as f:
        content = f.read()
    
    required_keys = [
        "GROQ_API_KEY",
        "DEEPGRAM_API_KEY", 
        "CARTESIA_API_KEY",
        "DAILY_API_KEY"
    ]
    
    missing = []
    for key in required_keys:
        if f"{key}=your_" in content or f"{key}=dg_" in content or f"{key}=gsk_" in content:
            if "your_key" in content or f"{key}=dg_" in content:
                missing.append(key)
    
    if missing:
        print(f"   ⚠️  Missing API keys: {', '.join(missing)}")
        print("   Please add them to .env file")
        return False
    
    print("   ✅ All required API keys present")
    return True


def create_data_dir():
    """Create data directory"""
    print("\n📁 Creating data directory...")
    Path("data").mkdir(exist_ok=True)
    print("   ✅ Data directory ready")
    return True


def main():
    """Main setup function"""
    print("=" * 60)
    print("🚀 VoixAI v3.0 - Local Development Setup")
    print("=" * 60)
    
    steps = [
        ("Check Docker", check_docker),
        ("Create data directory", create_data_dir),
        ("Setup virtual environment", setup_venv),
        ("Install dependencies", install_deps),
        ("Check environment file", check_env),
        ("Start local services", start_services),
    ]
    
    results = []
    for name, func in steps:
        try:
            results.append(func())
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ Setup complete!")
        print("\nNext steps:")
        print("  1. Ensure .env has all your API keys")
        print("  2. Activate virtual environment:")
        if os.name == "nt":
            print("     venv\\Scripts\\activate")
        else:
            print("     source venv/bin/activate")
        print("  3. Run the server:")
        print("     python src/main.py")
        print("  4. Open http://localhost:8000 in your browser")
    else:
        print("❌ Setup incomplete. Please fix the errors above.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
