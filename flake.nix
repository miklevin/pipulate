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
# 4. THIS FLAKE detects non-git directories and transforms them into git repos
# 5. Auto-updates are enabled through git pulls in future nix develop sessions
#
# === CURRENT IMPLEMENTATION ===
# The flake now fully implements the "magic cookie" functionality:
# - Detects non-git directories and transforms them into git repositories
# - Preserves critical files during transformation:
#   * app_name.txt (maintains app identity)
#   * .ssh directory (preserves credentials)
#   * .venv directory (preserves virtual environment)
# - Creates backups before transformation
# - Performs automatic git pulls to keep the installation up to date
# - Switches to SSH-based git operations when SSH keys are available
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
    let
      version = "1.0.5 (Stable Jupyter Workspace)";  # Updated version to reflect stable workspace
    in
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

        # Define a static workspace name to prevent random file generation
        jupyterWorkspaceName = "pipulate-main";

        # New script to handle JupyterLab configuration safely
        setupJupyterPrefs = pkgs.writeShellScriptBin "setup-jupyter-prefs" ''
          #!/usr/bin/env bash
          set -e
          # This script sets up project-local JupyterLab preferences.
          # It's called from the flake's shellHook and helper scripts.
          if [ -z "$JUPYTER_CONFIG_DIR" ]; then
              echo "Error: JUPYTER_CONFIG_DIR must be set." >&2
              exit 1
          fi

          JUPYTER_PREFS_DIR="$JUPYTER_CONFIG_DIR/lab/user-settings"
          
          # --- Theme Settings ---
          THEME_DIR="$JUPYTER_PREFS_DIR/@jupyterlab/apputils-extension"
          mkdir -p "$THEME_DIR"
          echo '{"theme": "JupyterLab Dark"}' > "$THEME_DIR/themes.json"

          # --- Code Editor Settings ---
          CODEMIRROR_DIR="$JUPYTER_PREFS_DIR/@jupyterlab/codemirror-extension"
          mkdir -p "$CODEMIRROR_DIR"
          echo '{"fontSize": 16, "theme": "material-darker"}' > "$CODEMIRROR_DIR/plugin.json"

          # --- Notebook UI Settings ---
          NOTEBOOK_DIR="$JUPYTER_PREFS_DIR/@jupyterlab/notebook-extension"
          mkdir -p "$NOTEBOOK_DIR"
          echo '{"codeCellConfig": {"fontSize": 16, "lineHeight": 1.4}}' > "$NOTEBOOK_DIR/tracker.json"
        '';

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
          nbstripout                   # Git filter for stripping notebook outputs
          setupJupyterPrefs            # Add the new script to the environment
        ] ++ (with pkgs; pkgs.lib.optionals isLinux [
          virtualenv
          gcc                          # GNU Compiler Collection for compiling C/C++ code
          stdenv.cc.cc.lib             # Standard C library for Linux systems
          chromedriver                 # ChromeDriver for Selenium automation
          chromium                     # Chromium browser for Selenium automation
        ]);

        # Define notebook paths for the copy-on-first-run solution
        originalNotebook = "helpers/botify/botify_api.ipynb";
        localNotebook = "notebook_introduction_local.ipynb";

        # This script sets up our Python environment and project
        runScript = pkgs.writeShellScriptBin "run-script" ''
          #!/usr/bin/env bash
          
          # Activate the virtual environment
          source .venv/bin/activate

          # Define function to copy notebook if needed (copy-on-first-run solution)
          copy_notebook_if_needed() {
            if [ -f "${originalNotebook}" ] && [ ! -f "${localNotebook}" ]; then
              echo "INFO: Creating a local introduction notebook in the project root..."
              echo "      Your work will be saved in '${localNotebook}' and will not interfere with updates."
              cp "${originalNotebook}" "${localNotebook}"
              echo "      To get future updates to the original notebook, you can delete '${localNotebook}'."
            fi
          }

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
          echo "Version: ${version}"
          if [ -n "$IN_NIX_SHELL" ] || [[ "$PS1" == *"(nix)"* ]]; then 
            echo "✓ In Nix shell v${version} - you can run python server.py"
          else 
            echo "✗ Not in Nix shell - please run nix develop"
          fi
          echo "Welcome to the $PROPER_APP_NAME development environment on ${system}!"
          echo 

          # --- JupyterLab Local Configuration ---
          # Set env var and run setup script for the main 'nix develop' command
          export JUPYTER_CONFIG_DIR="$(pwd)/.jupyter"
          setup-jupyter-prefs
          echo "✓ JupyterLab preferences set for dark theme and larger fonts."

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
          cat << 'START_SCRIPT_EOF' > .venv/bin/start
          #!/bin/sh
          export JUPYTER_CONFIG_DIR="$(pwd)/.jupyter"
          setup-jupyter-prefs
          copy_notebook_if_needed
          echo "A JupyterLab tab will open in your default browser."
          tmux kill-session -t jupyter 2>/dev/null || echo "No tmux session named 'jupyter' is running."
          tmux new-session -d -s jupyter "source .venv/bin/activate && jupyter lab ${localNotebook} --workspace=${jupyterWorkspaceName} --NotebookApp.token=\"\" --NotebookApp.password=\"\" --NotebookApp.disable_check_xsrf=True"
          echo "If no tab opens, visit http://localhost:8888/lab"
          echo "To view JupyterLab server: tmux attach -t jupyter"
          echo "To stop JupyterLab server: stop"
          START_SCRIPT_EOF
          chmod +x .venv/bin/start

          cat << 'STOP_SCRIPT_EOF' > .venv/bin/stop
          #!/bin/sh
          echo "Stopping tmux session 'jupyter'..."
          tmux kill-session -t jupyter 2>/dev/null || echo "No tmux session named 'jupyter' is running."
          echo "The tmux session 'jupyter' has been stopped."
          STOP_SCRIPT_EOF
          chmod +x .venv/bin/stop
          
          # Create a run-server script
          cat << 'SERVER_SCRIPT_EOF' > .venv/bin/run-server
          #!/bin/sh
          echo "Starting $APP_NAME server..."
          # Kill any running server instances first
          pkill -f "python server.py" || true
          # Always pull the latest code before starting the server
          echo "Pulling latest code updates..."
          git pull
          python server.py
          SERVER_SCRIPT_EOF
          chmod +x .venv/bin/run-server
          
          # Create a run-jupyter script
          cat << 'JUPYTER_SCRIPT_EOF' > .venv/bin/run-jupyter
          #!/bin/sh
          export JUPYTER_CONFIG_DIR="$(pwd)/.jupyter"
          setup-jupyter-prefs
          echo "Starting JupyterLab..."
          copy_notebook_if_needed
          
          # Kill existing jupyter tmux session
          tmux kill-session -t jupyter 2>/dev/null || true
          
          # Start JupyterLab
          tmux new-session -d -s jupyter "source .venv/bin/activate && jupyter lab ${localNotebook} --workspace=${jupyterWorkspaceName} --NotebookApp.token=\"\" --NotebookApp.password=\"\" --NotebookApp.disable_check_xsrf=True"
          
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
          JUPYTER_SCRIPT_EOF
          chmod +x .venv/bin/run-jupyter
          
          # Create a run-all script to restart both servers
          cat << 'RUN_ALL_SCRIPT_EOF' > .venv/bin/run-all
          #!/bin/sh
          export JUPYTER_CONFIG_DIR="$(pwd)/.jupyter"
          setup-jupyter-prefs
          echo "JupyterLab will start in the background."
          copy_notebook_if_needed
          
          # Kill existing tmux sessions
          tmux kill-session -t jupyter 2>/dev/null || true
          
          # Kill any running server instances
          pkill -f "python server.py" || true
          
          # Start JupyterLab
          echo "Starting JupyterLab..."
          tmux new-session -d -s jupyter "source .venv/bin/activate && jupyter lab ${localNotebook} --workspace=${jupyterWorkspaceName} --NotebookApp.token=\"\" --NotebookApp.password=\"\" --NotebookApp.disable_check_xsrf=True"
          
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
          
          # Always pull the latest code before starting the server
          echo "Pulling latest code updates..."
          git pull
          
          # Open FastHTML in the browser
          (
            # Wait a brief moment to ensure browser doesn't get confused with multiple tabs
            sleep 10
            if command -v xdg-open >/dev/null 2>&1; then
              xdg-open http://localhost:5001 >/dev/null 2>&1 &
            elif command -v open >/dev/null 2>&1; then
              open http://localhost:5001 >/dev/null 2>&1 &
            fi
          ) &
          
          # Run server in foreground
          python server.py
          RUN_ALL_SCRIPT_EOF
          chmod +x .venv/bin/run-all
          
          # Add convenience scripts to PATH
          export PATH="$VIRTUAL_ENV/bin:$PATH"
          
          # Automatically start JupyterLab in background and server in foreground
          # Start JupyterLab in a tmux session
          copy_notebook_if_needed
          tmux kill-session -t jupyter 2>/dev/null || true
          tmux new-session -d -s jupyter "source .venv/bin/activate && jupyter lab ${localNotebook} --workspace=${jupyterWorkspaceName} --NotebookApp.token=\"\" --NotebookApp.password=\"\" --NotebookApp.disable_check_xsrf=True"
          
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
          
          # Always pull the latest code before starting the server
          echo "Pulling latest code updates..."
          git pull
          
          # Open FastHTML in the browser
          (
            # Wait a brief moment to ensure browser doesn't get confused with multiple tabs
            sleep 10
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
          # Set up nbstripout git filter
          if [ ! -f .gitattributes ]; then
            echo "*.ipynb filter=nbstripout" > .gitattributes
          fi
          git config --local filter.nbstripout.clean "nbstripout"
          git config --local filter.nbstripout.required true
          
          # Set EFFECTIVE_OS for browser automation scripts
          if [[ "$(uname -s)" == "Darwin" ]]; then
            export EFFECTIVE_OS="darwin"
          else
            # Assuming Linux for non-Darwin POSIX systems in Nix context
            export EFFECTIVE_OS="linux"
          fi
          echo "INFO: EFFECTIVE_OS set to: $EFFECTIVE_OS (for browser automation context)"
          
          # Add isnix alias for environment checking
          alias isnix='if [ -n "$IN_NIX_SHELL" ] || [[ "$PS1" == *"(nix)"* ]]; then echo "✓ In Nix shell v${version} - you can run python server.py"; else echo "✗ Not in Nix shell - please run nix develop"; fi'
          
          # Add a more visible prompt when in Nix shell
          if [ -n "$IN_NIX_SHELL" ] || [[ "$PS1" == *"(nix)"* ]]; then
            export PS1="(nix) $PS1"
            echo "You are now in the Nix development environment. Type 'exit' to leave it."
          fi
          
          # MAGIC COOKIE TRANSFORMATION
          if [ ! -d .git ]; then
            echo "🔄 Transforming installation into git repository..."
            
            # Create a temporary directory for the clean git clone
            TEMP_DIR=$(mktemp -d)
            echo "Creating temporary clone in $TEMP_DIR..."
            
            # Clone the repository into the temporary directory
            if git clone --depth=1 https://github.com/miklevin/pipulate.git "$TEMP_DIR"; then
              # Save important files that need to be preserved
              echo "Preserving app identity and credentials..."
              if [ -f app_name.txt ]; then
                cp app_name.txt "$TEMP_DIR/"
              fi
              if [ -d .ssh ]; then
                mkdir -p "$TEMP_DIR/.ssh"
                cp -r .ssh/* "$TEMP_DIR/.ssh/"
                chmod 600 "$TEMP_DIR/.ssh/rot" 2>/dev/null || true
              fi
              
              # Preserve virtual environment if it exists
              if [ -d .venv ]; then
                echo "Preserving virtual environment..."
                cp -r .venv "$TEMP_DIR/"
              fi
              
              # Get current directory name and parent for later restoration
              CURRENT_DIR="$(pwd)"
              PARENT_DIR="$(dirname "$CURRENT_DIR")"
              DIR_NAME="$(basename "$CURRENT_DIR")"
              
              # Move everything to a backup location first
              BACKUP_DIR=$(mktemp -d)
              echo "Creating backup of current directory in $BACKUP_DIR..."
              cp -r . "$BACKUP_DIR/"
              
              # Clean current directory (except hidden files to avoid issues)
              find . -maxdepth 1 -not -path "./.*" -exec rm -rf {} \; 2>/dev/null || true
              
              # Move git repository contents into current directory
              echo "Moving git repository into place..."
              cp -r "$TEMP_DIR/." .
              
              # Clean up temporary directory
              rm -rf "$TEMP_DIR"
              
              echo "✅ Successfully transformed into git repository!"
              echo "Original files backed up to: $BACKUP_DIR"
              echo "You can safely remove the backup once everything is working:"
              echo "rm -rf \"$BACKUP_DIR\""
              
            else
              echo "❌ Error: Failed to clone repository. Your installation will continue,"
              echo "but without git-based updates. Please try again later or report this issue."
            fi
          fi
          
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
          
          # Update remote URL to use SSH if we have a key
          if [ -d .git ] && [ -f ~/.ssh/id_rsa ]; then
            # Check if we're using HTTPS remote
            REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
            if [[ "$REMOTE_URL" == https://* ]]; then
              echo "Updating remote URL to use SSH..."
              git remote set-url origin git@github.com:miklevin/pipulate.git
            fi
          fi
          
          # Set up the Python virtual environment
          test -d .venv || ${pkgs.python3}/bin/python -m venv .venv
          export VIRTUAL_ENV="$(pwd)/.venv"
          export PATH="$VIRTUAL_ENV/bin:$PATH"
          export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath commonPackages}:$LD_LIBRARY_PATH

          # --- Ensure .jupyter directory is in .gitignore ---
          if [ -f .gitignore ]; then
            # Add .jupyter/ to .gitignore if not already present
            grep -qxF '.jupyter/' .gitignore || echo '.jupyter/' >> .gitignore
          fi

          # --- JupyterLab Local Configuration ---
          # Set env var and run setup script for interactive shells
          export JUPYTER_CONFIG_DIR="$(pwd)/.jupyter"
          setup-jupyter-prefs

          # Set up CUDA env vars if available (no output) - Linux only
          ${pkgs.lib.optionalString isLinux ''
          if command -v nvidia-smi &> /dev/null; then
            export CUDA_HOME=${pkgs.cudatoolkit}
            export PATH=$CUDA_HOME/bin:$PATH
            export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
          fi
          ''}

          # Set up the SSH key if it exists
          if [ -f .ssh/rot ]; then
            # Create an id_rsa file for the git operations by decoding the ROT13 key
            mkdir -p ~/.ssh
            
            # Decode the ROT13 key to ~/.ssh/id_rsa if it doesn't exist
            if [ ! -f ~/.ssh/id_rsa ]; then
              echo "Setting up SSH key for git operations..."
              tr 'A-Za-z' 'N-ZA-Mn-za-m' < .ssh/rot > ~/.ssh/id_rsa
              chmod 600 ~/.ssh/id_rsa
              
              # Create or append to SSH config to use this key for github
              if ! grep -q "Host github.com" ~/.ssh/config 2>/dev/null; then
                cat >> ~/.ssh/config << EOF
Host github.com
  IdentityFile ~/.ssh/id_rsa
  User git
EOF
              fi
              
              # Add github.com to known_hosts if not already there
              if ! grep -q "github.com" ~/.ssh/known_hosts 2>/dev/null; then
                ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
              fi
            fi
          fi
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
              # Set up the Python virtual environment (minimal, no pip install)
              test -d .venv || ${pkgs.python3}/bin/python -m venv .venv
              export VIRTUAL_ENV="$(pwd)/.venv"
              export PATH="$VIRTUAL_ENV/bin:$PATH"
              export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath commonPackages}:$LD_LIBRARY_PATH
              
              # --- JupyterLab Local Configuration for Quiet Shell ---
              export JUPYTER_CONFIG_DIR="$(pwd)/.jupyter"
              # We don't need to run the setup script here, as the env var is enough
              # to make Jupyter use the config files if they exist.
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
