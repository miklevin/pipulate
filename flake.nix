#       ____                      _       _                        .--.      ___________
#      |  _ \  __ _ _ ____      _(_)_ __ (_)_  __    ,--./,-.     |o_o |    |     |     |
#      | | | |/ _` | '__\ \ /\ / / | '_ \| \ \/ /   / #      \    |:_/ |    |     |     |
#      | |_| | (_| | |   \ V  V /| | | | | |>  <   |          |  //   \ \   |_____|_____|
#      |____/ \__,_|_|    \_/\_/ |_|_| |_|_/_/\_\   \        /  (|     | )  |     |     |
#                                                    `._,._,'  /'\_   _/`\  |     |     |
#      Solving the "Not on my machine" problem well.           \___)=(___/  |_____|_____|

# ==============================================================================
# PIPULATE NIX FLAKE - "MAGIC COOKIE" AUTO-UPDATING SYSTEM
# ==============================================================================
# 
# This flake is the second half of the "magic cookie" installation system.
# It works together with the install.sh script (hosted at pipulate.com) to:
#
# 1. Transform a non-git directory into a proper git repository
# 2. Enable forever-forward git-pull auto-updates
# 3. Provide a consistent development environment across macOS and Linux
#
# === THE "MAGIC COOKIE" CONCEPT ===
# The "magic cookie" approach solves a bootstrapping problem:
# - Nix flakes require a git repository to function properly
# - We can't rely on git being available on all systems during initial install
# - We want a simple one-line curl|sh installation that works everywhere
#
# The solution:
# 1. install.sh downloads a ZIP archive (no git required)
# 2. install.sh extracts the ZIP and adds a ROT13-encoded SSH key
# 3. install.sh runs `nix develop` to activate this flake
# 4. THIS FLAKE should detect it's not in a git repo and transform itself
# 5. Auto-updates are enabled through git pulls in future nix develop sessions
#
# === CURRENT LIMITATIONS ===
# The current flake implementation is missing critical "magic cookie" functionality:
# - It doesn't check if it's running in a git repository
# - It doesn't perform a clean git clone to transform the installation
# - It doesn't preserve app_name.txt during the transformation
# - It doesn't move the .ssh directory with keys during transformation
#
# === THE PATH FORWARD ===
# To complete the "magic cookie" system, this flake needs to be enhanced:
# 1. In baseEnvSetup: Add detection for non-git directories
# 2. Clone the repo to a temporary location when needed
# 3. Preserve app_name.txt and .ssh during the transformation
# 4. Swap directories to upgrade the installation
#
# === REPOSITORY AWARENESS ===
# This flake is part of the target pipulate project repo at:
# /home/mike/repos/pipulate/flake.nix
#
# This is different from the installer script which lives at:
# /home/mike/repos/Pipulate.com/install.sh
#
# When a user runs:
#   curl -L https://pipulate.com/install.sh | sh -s Botifython
# The installer downloads this flake as part of the ZIP archive.

# Most modern development is done on Linux, but Macs are Unix. If you think Homebrew and Docker
# are the solution, you're wrong. Welcome to the world of Nix Flakes! This file defines a complete,
# reproducible development environment. It's like a recipe for your perfect workspace, ensuring
# everyone on your team has the exact same setup, every time. As a bonus, you can use Nix flakes on
# Windows under WSL. Plus, whatever you make will be deployable to the cloud.

{
  # This description helps others understand the purpose of this Flake
  description = "A flake that reports the OS using separate scripts with optional CUDA support and unfree packages allowed.";
  
  # Inputs are the dependencies for our Flake
  # They're pinned to specific versions to ensure reproducibility
  inputs = {
    # nixpkgs is the main repository of Nix packages
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # flake-utils provides helpful functions for working with Flakes
    flake-utils.url = "github:numtide/flake-utils";
  };

  # Outputs define what our Flake produces
  # In this case, it's a development shell that works across different systems
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # We're creating a custom instance of nixpkgs
        # This allows us to enable unfree packages like CUDA
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;  # This is necessary for CUDA support
          };
        };

        # These helpers let us adjust our setup based on the OS
        isDarwin = pkgs.stdenv.isDarwin;
        isLinux = pkgs.stdenv.isLinux;

        # Common packages that we want available in our environment
        # regardless of the operating system
        commonPackages = with pkgs; [
          python3Full                  # Python 3.x interpreter (highest stable?)
          figlet                       # For creating ASCII art welcome messages
          tmux                         # Terminal multiplexer for managing sessions
          zlib                         # Compression library for data compression
          git                          # Version control system for tracking changes
          curl                         # Command-line tool for transferring data with URLs
          wget                         # Utility for non-interactive download of files from the web
          cmake                        # Cross-platform build system generator
          htop                         # Interactive process viewer for Unix systems
        ] ++ (with pkgs; pkgs.lib.optionals isLinux [
          virtualenv
          gcc                          # GNU Compiler Collection for compiling C/C++ code
          stdenv.cc.cc.lib             # Standard C library for Linux systems
        ]);

        # This script sets up our Python environment and project
        runScript = pkgs.writeShellScriptBin "run-script" ''
          #!/usr/bin/env bash
          
          # Activate the virtual environment
          source .venv/bin/activate

          # Create a fancy welcome message
          if [ ! -f app_name.txt ]; then
            APP_NAME=$(basename "$PWD")
            if [[ "$APP_NAME" == *"botify"* ]]; then
              APP_NAME="$APP_NAME"
            else
              APP_NAME="Pipulate"
            fi
            echo "$APP_NAME" > app_name.txt
          fi
          # MAGIC COOKIE COMPONENT: This section reads the app_name.txt that should be 
          # preserved if/when the directory is transformed into a git repo
          APP_NAME=$(cat app_name.txt)
          PROPER_APP_NAME=$(echo "$APP_NAME" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')
          figlet "$PROPER_APP_NAME"
          echo "Welcome to the $PROPER_APP_NAME development environment on ${system}!"
          echo 

          # Install Python packages from requirements.txt
          # This allows flexibility to use the latest PyPI packages
          # Note: This makes the environment less deterministic
          echo "- Confirming pip packages..."
          if pip install --upgrade pip --quiet && \
            pip install -r requirements.txt --quiet; then
              package_count=$(pip list --format=freeze | wc -l)
              echo "- Done. $package_count pip packages present."
          else
              echo "Warning: An error occurred during pip setup."
          fi

          # Check if numpy is properly installed
          if python -c "import numpy" 2>/dev/null; then
            echo "- numpy is importable (good to go!)"
            echo
            echo "Starting JupyterLab and $APP_NAME server automatically..."
            echo "Both will open in your browser..."
            echo
            echo "To view server logs: tmux attach -t server"
            echo "To view JupyterLab logs: tmux attach -t jupyter"
            echo "To stop all services: pkill tmux"
            echo "To restart all services: run-all"
            echo "To start only server: run-server"
            echo "To start only JupyterLab: run-jupyter"
          else
            echo "Error: numpy could not be imported. Check your installation."
          fi

          # Create convenience scripts for managing JupyterLab
          # Note: We've disabled token and password for easier access, especially in WSL environments
          cat << EOF > .venv/bin/start
          #!/bin/sh
          echo "A JupyterLab tab will open in your default browser."
          tmux kill-session -t jupyter 2>/dev/null || echo "No tmux session named 'jupyter' is running."
          tmux new-session -d -s jupyter "source .venv/bin/activate && jupyter lab --NotebookApp.token=\"\" --NotebookApp.password=\"\" --NotebookApp.disable_check_xsrf=True"
          echo "If no tab opens, visit http://localhost:8888/lab"
          echo "To view JupyterLab server: tmux attach -t jupyter"
          echo "To stop JupyterLab server: stop"
          EOF
          chmod +x .venv/bin/start

          cat << EOF > .venv/bin/stop
          #!/bin/sh
          echo "Stopping tmux session 'jupyter'..."
          tmux kill-session -t jupyter 2>/dev/null || echo "No tmux session named 'jupyter' is running."
          echo "The tmux session 'jupyter' has been stopped."
          EOF
          chmod +x .venv/bin/stop
          
          # Create a run-server script
          cat << EOF > .venv/bin/run-server
          #!/bin/sh
          echo "Starting $APP_NAME server..."
          # Kill any running server instances first
          pkill -f "python server.py" || true
          python server.py
          EOF
          chmod +x .venv/bin/run-server
          
          # Create a run-jupyter script
          cat << EOF > .venv/bin/run-jupyter
          #!/bin/sh
          echo "Starting JupyterLab..."
          
          # Kill existing jupyter tmux session
          tmux kill-session -t jupyter 2>/dev/null || true
          
          # Start JupyterLab
          tmux new-session -d -s jupyter "source .venv/bin/activate && jupyter lab --NotebookApp.token=\"\" --NotebookApp.password=\"\" --NotebookApp.disable_check_xsrf=True"
          
          # Wait for JupyterLab to start
          echo "JupyterLab is starting..."
          for i in {1..30}; do
            if curl -s http://localhost:8888 > /dev/null; then
              echo "JupyterLab is ready!"
              break
            fi
            sleep 1
            echo -n "."
          done
          
          echo "JupyterLab started! View logs with: tmux attach -t jupyter"
          EOF
          chmod +x .venv/bin/run-jupyter
          
          # Create a run-all script to restart both servers
          cat << EOF > .venv/bin/run-all
          #!/bin/sh
          echo "JupyterLab will start in the background."
          
          # Kill existing tmux sessions
          tmux kill-session -t jupyter 2>/dev/null || true
          
          # Kill any running server instances
          pkill -f "python server.py" || true
          
          # Start JupyterLab
          echo "Starting JupyterLab..."
          tmux new-session -d -s jupyter "source .venv/bin/activate && jupyter lab --NotebookApp.token=\"\" --NotebookApp.password=\"\" --NotebookApp.disable_check_xsrf=True"
          
          # Wait for JupyterLab to start
          echo "JupyterLab is starting..."
          for i in {1..30}; do
            if curl -s http://localhost:8888 > /dev/null; then
              echo "JupyterLab is ready!"
              break
            fi
            sleep 1
            echo -n "."
          done
          
          echo "JupyterLab started in the background. View logs with: tmux attach -t jupyter"
          echo "Starting $APP_NAME server in the foreground..."
          
          # Open FastHTML in the browser
          (
            # Wait a brief moment to ensure browser doesn't get confused with multiple tabs
            sleep 7
            if command -v xdg-open >/dev/null 2>&1; then
              xdg-open http://localhost:5001 >/dev/null 2>&1 &
            elif command -v open >/dev/null 2>&1; then
              open http://localhost:5001 >/dev/null 2>&1 &
            fi
          ) &
          
          # Run server in foreground
          python server.py
          EOF
          chmod +x .venv/bin/run-all
          
          # Add convenience scripts to PATH
          export PATH="$VIRTUAL_ENV/bin:$PATH"
          
          # Automatically start JupyterLab in background and server in foreground
          # Start JupyterLab in a tmux session
          tmux kill-session -t jupyter 2>/dev/null || true
          tmux new-session -d -s jupyter "source .venv/bin/activate && jupyter lab --NotebookApp.token=\"\" --NotebookApp.password=\"\" --NotebookApp.disable_check_xsrf=True"
          
          # Wait for JupyterLab to start
          echo "JupyterLab is starting..."
          for i in {1..30}; do
            if curl -s http://localhost:8888 > /dev/null; then
              echo "JupyterLab is ready!"
              break
            fi
            sleep 1
            echo -n "."
          done
          
          # Kill any running server instances
          pkill -f "python server.py" || true
          
          # Start the server in foreground
          echo "Starting $APP_NAME server in the foreground..."
          echo "Press Ctrl+C to stop the server."
          
          # Open FastHTML in the browser
          (
            # Wait a brief moment to ensure browser doesn't get confused with multiple tabs
            sleep 7
            if command -v xdg-open >/dev/null 2>&1; then
              xdg-open http://localhost:5001 >/dev/null 2>&1 &
            elif command -v open >/dev/null 2>&1; then
              open http://localhost:5001 >/dev/null 2>&1 &
            fi
          ) &
          
          # Run server in foreground
          python server.py
        '';

        # Base shell hook that just sets up the environment without any output
        baseEnvSetup = pkgs: ''
          # MAGIC COOKIE CRITICAL COMPONENT: 
          # This section should detect if we're not in a git repository
          # and perform the "magic cookie" transformation.
          #
          # MISSING FUNCTIONALITY:
          # 1. Check if .git directory doesn't exist
          # 2. Create temp directory and git clone the repo there
          # 3. Preserve app_name.txt and .ssh directory
          # 4. Swap the directories to upgrade the installation
          # 5. Clean up temporary directories

          # Auto-update: Perform a git pull if this is a git repository
          if [ -d .git ]; then
            echo "Checking for updates..."
            git fetch origin
            LOCAL=$(git rev-parse HEAD)
            REMOTE=$(git rev-parse @{u})
            
            if [ "$LOCAL" != "$REMOTE" ]; then
              echo "Updates found. Pulling latest changes..."
              git pull --ff-only
              echo "Update complete!"
            else
              echo "Already up to date."
            fi
          fi
          
          # Set up the Python virtual environment
          test -d .venv || ${pkgs.python3}/bin/python -m venv .venv
          export VIRTUAL_ENV="$(pwd)/.venv"
          export PATH="$VIRTUAL_ENV/bin:$PATH"
          export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath commonPackages}:$LD_LIBRARY_PATH

          # Set up CUDA env vars if available (no output) - Linux only
          ${pkgs.lib.optionalString isLinux ''
          if command -v nvidia-smi &> /dev/null; then
            export CUDA_HOME=${pkgs.cudatoolkit}
            export PATH=$CUDA_HOME/bin:$PATH
            export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
          fi
          ''}
        '';

        # Function to create shells for each OS
        mkShells = pkgs: {
          # Default shell with the full interactive setup
          default = pkgs.mkShell {
            buildInputs = commonPackages ++ (with pkgs; pkgs.lib.optionals 
              (isLinux && builtins.pathExists "/usr/bin/nvidia-smi") 
              cudaPackages
            );
            shellHook = ''
              # Kill any running server instances first
              pkill -f "python server.py" || true
              
              ${baseEnvSetup pkgs}
              
              # Set up CUDA if available (with output)
              if ${if isLinux then "command -v nvidia-smi &> /dev/null" else "false"}; then
                echo "CUDA hardware detected."
              else
                echo "No CUDA hardware detected."
              fi
              
              # Run the full interactive script
              ${runScript}/bin/run-script
            '';
          };
          
          # Quiet shell for AI assistants and scripting
          quiet = pkgs.mkShell {
            buildInputs = commonPackages ++ (with pkgs; pkgs.lib.optionals 
              (isLinux && builtins.pathExists "/usr/bin/nvidia-smi") 
              cudaPackages
            );
            shellHook = ''
              # Kill any running server instances first
              pkill -f "python server.py" || true
              
              ${baseEnvSetup pkgs}
              # Minimal confirmation, can be removed for zero output
              echo "Quiet Nix environment activated."
            '';
          };
        };

        # Get the shells for the current OS
        shells = mkShells pkgs;

      in {
        # Multiple devShells for different use cases
        devShells = shells;
        
        # The default devShell (when just running 'nix develop')
        devShell = shells.default;
      });
}
