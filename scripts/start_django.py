#!/usr/bin/env python
import os
import sys
import subprocess
import time

def main():
    print("🚀 Starting LootLink Django Server...")
    print("=====================================")
    
    # Change to project directory
    os.chdir(r'C:\Users\ivanp\Desktop\LootLink')
    print(f"Working directory: {os.getcwd()}")
    
    # Create migrations
    print("\n📝 Creating migrations...")
    try:
        subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'accounts'], check=True)
        subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'listings'], check=True)
        subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)
        print("✅ Migrations completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Migration warning: {e}")
        print("Continuing anyway...")
    
    # Start server
    print("\n🌐 Starting Django development server...")
    print("Server will be available at: http://127.0.0.1:8000")
    print("Press Ctrl+C to stop the server")
    print("=====================================\n")
    
    try:
        subprocess.run([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000'])
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == '__main__':
    main()
