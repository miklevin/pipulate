#       ____                      _       _                        .--.      ___________
#      |  _ \  __ _ _ ____      _(_)_ __ (_)_  __    ,--./,-.     |o_o |    |     |     |
#      | | | |/ _` | '__\ \ /\ / / | '_ \| \ \/ /   / #      \    |:_/ |    |     |     |
#      | |_| | (_| | |   \ V  V /| | | | | |>  <   |          |  //   \ \   |_____|_____|
#      |____/ \__,_|_|    \_/\_/ |_|_| |_|_/_/\_\   \        /  (|     | )  |     |     |
#                                                    `._,._,'  /'\_   _/`\  |     |     |
#      Solving the "Not on my machine" problem well.           \___)=(___/  |_____|_____|

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
        # Define the project name variable here
        projectName = "pipulate";

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
          python313Full              # Python 3.11 interpreter
          # python311.pkgs.pip         # Package installer for Python
          # python311.pkgs.virtualenv  # Tool to create isolated Python environments
          figlet                     # For creating ASCII art welcome messages
          tmux                       # Terminal multiplexer for managing sessions
          zlib                       # Compression library for data compression
          git                        # Version control system for tracking changes
          curl                       # Command-line tool for transferring data with URLs
          wget                       # Utility for non-interactive download of files from the web
          cmake                      # Cross-platform build system generator
          htop                       # Interactive process viewer for Unix systems
        ] ++ (with pkgs; pkgs.lib.optionals isLinux [
          gcc                        # GNU Compiler Collection for compiling C/C++ code
          stdenv.cc.cc.lib           # Standard C library for Linux systems
        ]);

        # This script sets up our Python environment and project
        runScript = pkgs.writeShellScriptBin "run-script" ''
          #!/usr/bin/env bash
          
          # Use the projectName variable
          REPO_NAME="${projectName}"
          REPO_NAME=''${REPO_NAME%-main}  # Remove "-main" suffix if it exists
          PROPER_REPO_NAME=$(echo "$REPO_NAME" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')
          figlet "$PROPER_REPO_NAME"
          echo "Welcome to the $PROPER_REPO_NAME development environment on ${system}!"
          echo 

          # Function to setup virtual environment
          setup_venv() {
            test -d .venv || ${pkgs.python313Full}/bin/python -m venv .venv
            source .venv/bin/activate
            echo "- Checking pip packages..."
            if pip install --upgrade pip --quiet && \
              pip install -r requirements.txt --quiet; then
                package_count=$(pip list --format=freeze | wc -l)
                echo "- Done. $package_count pip packages installed."
            else
                echo "Warning: An error occurred during pip setup."
            fi
          }

          # Try initial setup
          setup_venv

          # If numpy fails, rebuild venv from scratch
          if ! python -c "import numpy" 2>/dev/null; then
            echo "numpy import failed - rebuilding virtual environment..."
            deactivate 2>/dev/null || true
            rm -rf .venv
            setup_venv
          fi

          # Only perform git operations if projectName is "botifython"
          if [ "${projectName}" = "botifython" ]; then
            # Decrypt the private key
            # Check if key is in .ssh/
            if [ -f ./.ssh/rot ]; then
              cat ./.ssh/rot | tr 'A-Za-z' 'N-ZA-Mn-za-m' > ./.ssh/key
              chmod 600 ./.ssh/key
            fi

            # Check if there is a .git folder
            if [ -d .git ]; then
              echo "Pulling latest changes from git..."
              GIT_SSH_COMMAND='ssh -i ./.ssh/key' git pull
            else
              # Clone the repository into a temporary directory
              echo "Cloning repository..."
              git clone -c "core.sshCommand=ssh -i ./.ssh/key" git@github.com:${projectName}/${projectName}.git /tmp/${projectName}
              # Move the contents of the temporary directory to the current directory
              mv /tmp/${projectName}/* .
              mv /tmp/${projectName}/.git .
              rm -rf /tmp/${projectName}
            fi
            echo
          fi

          # Check if numpy is properly installed
          if python -c "import numpy" 2>/dev/null; then
            echo "- numpy is importable (good to go!)"
            echo
            echo "To start JupyterLab, type: start"
            echo "To stop JupyterLab, type: stop"
            echo
          else
            echo "Error: numpy could not be imported. Check your installation."
          fi

          # IMPORTANT: Do not remove or modify the following script creations.
          # They're essential for the 'botifython', 'bf', 'start', and 'stop' command functionalities.
          
          # CRITICAL: This line removes existing files to prevent symbolic link issues.
          # Do not remove this line as it ensures clean script creation.
          rm -f .venv/bin/${projectName} .venv/bin/bf .venv/bin/start .venv/bin/stop

          # IMPORTANT: Update the script creations to use the projectName variable
          cat << EOF > .venv/bin/${projectName}
          #!/usr/bin/env bash

          # Function to open URL in the default browser
          open_url() {
            if [[ "$OSTYPE" == "darwin"* ]]; then
              open "http://localhost:5001"
            elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
              if [[ -n "$WSL_DISTRO_NAME" ]]; then
                powershell.exe /c start "http://localhost:5001"
              else
                xdg-open "http://localhost:5001" || sensible-browser "http://localhost:5001" || x-www-browser "http://localhost:5001" || gnome-open "http://localhost:5001"
              fi
            else
              echo "Unsupported operating system. Please open http://localhost:5001 in your browser manually."
            fi
          }

          (sleep 10 && open_url) &

          python "$PWD/${projectName}.py"
          EOF
          chmod +x .venv/bin/${projectName}

          cat << EOF > .venv/bin/bf
          #!/usr/bin/env bash

          python "$PWD/${projectName}.py"
          EOF
          chmod +x .venv/bin/bf

          cat << 'EOF' > .venv/bin/start
          #!/bin/sh
          echo "Starting JupyterLab in a tmux session..."
          tmux kill-session -t jupyter 2>/dev/null || echo "No existing tmux session named 'jupyter'."
          tmux new-session -d -s jupyter 'source .venv/bin/activate && jupyter lab --NotebookApp.token="" --NotebookApp.password="" --NotebookApp.disable_check_xsrf=True'
          echo "JupyterLab is now running in a tmux session named 'jupyter'."
          echo "To view JupyterLab server output: tmux attach -t jupyter"
          echo "To access JupyterLab, visit http://localhost:8888 in your browser."
          echo "To stop JupyterLab server: stop"
          EOF
          chmod +x .venv/bin/start

          cat << 'EOF' > .venv/bin/stop
          #!/bin/sh
          echo "Stopping JupyterLab tmux session..."
          tmux kill-session -t jupyter 2>/dev/null || echo "No tmux session named 'jupyter' is running."
          echo "The JupyterLab tmux session has been stopped."
          EOF
          chmod +x .venv/bin/stop

          # CRITICAL: Keep this PATH modification.
          # It ensures the custom scripts are accessible from the command line.
          # Do not remove or modify this export statement.
          export PATH="$PWD/.venv/bin:$PATH"

          # IMPORTANT: Keep these instructions for users.
          # They provide essential guidance on how to run the application and manage JupyterLab.
          echo "To run ${projectName}.py, type either '${projectName}' or 'bf'"
        '';

        # Define the development shell for Linux systems (including WSL)
        linuxDevShell = pkgs.mkShell {
          # Include common packages and conditionally add CUDA if available
          buildInputs = commonPackages ++ (with pkgs; pkgs.lib.optionals (builtins.pathExists "/usr/bin/nvidia-smi") cudaPackages);
          shellHook = ''
            # Set up the Python virtual environment
            test -d .venv || ${pkgs.python313Full}/bin/python -m venv .venv
            export VIRTUAL_ENV="$(pwd)/.venv"
            export PATH="$VIRTUAL_ENV/bin:$PATH"
            # Customize the prompt to show we're in a Nix environment
            export PS1='$(printf "\033[01;34m(nix) \033[00m\033[01;32m[%s@%s:%s]$\033[00m " "\u" "\h" "\w")'
            export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath commonPackages}:$LD_LIBRARY_PATH

            # Set up CUDA if available
            if command -v nvidia-smi &> /dev/null; then
              echo "CUDA hardware detected."
              export CUDA_HOME=${pkgs.cudatoolkit}
              export PATH=$CUDA_HOME/bin:$PATH
              export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
            else
              echo "No CUDA hardware detected."
            fi

            # IMPORTANT: Do not remove or modify the runScript execution.
            # It sets up the entire development environment.
            # Run our setup script
            ${runScript}/bin/run-script
          '';
        };

        # Define the development shell for macOS systems
        darwinDevShell = pkgs.mkShell {
          buildInputs = commonPackages;
          shellHook = ''
            # Set up the Python virtual environment
            test -d .venv || ${pkgs.python313Full}/bin/python -m venv .venv
            export VIRTUAL_ENV="$(pwd)/.venv"
            export PATH="$VIRTUAL_ENV/bin:$PATH"
            # Customize the prompt to show we're in a Nix environment
            export PS1='$(printf "\033[01;34m(nix) \033[00m\033[01;32m[%s@%s:%s]$\033[00m " "\u" "\h" "\w")'
            export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath commonPackages}:$LD_LIBRARY_PATH

            # IMPORTANT: Do not remove or modify the runScript execution.
            # It sets up the entire development environment.
            # Run our setup script
            ${runScript}/bin/run-script
          '';
        };

      in {
        # Choose the appropriate development shell based on the OS
        devShell = if isLinux then linuxDevShell else darwinDevShell;  # Ensure multi-OS support
      });
}
