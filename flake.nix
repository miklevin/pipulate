{
  #  ____  _             _       _          This is a Nix flake that defines a reproducible
  # |  _ \(_)_ __  _   _| | __ _| |_ ___    development environment for a project called
  # | |_) | | '_ \| | | | |/ _` | __/ _ \   Pipulate. This flake sets up a development shell
  # |  __/| | |_) | |_| | | (_| | ||  __/   with all necessary dependencies and includes
  # |_|   |_| .__/ \__,_|_|\__,_|\__\___|   scripts to start and stop services like JupyterLab
  #         |_|                             and a custom FastHTML server.                     


  # Define the external dependencies (other flakes) this flake uses
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.05";  # Nix packages source
    flake-utils.url = "github:numtide/flake-utils";    # Helpful utilities for flakes
  };

  # Define the outputs of this flake
  outputs = inputs @ { self, nixpkgs, flake-utils, ... }:
    # Generate outputs for each default system (e.g., x86_64-linux, aarch64-darwin)
    flake-utils.lib.eachDefaultSystem (system: let
      # Import nixpkgs for the current system, allowing unfree packages
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };

      # Import local configuration if it exists, otherwise use an empty set
      localConfig = if builtins.pathExists ./local.nix then import ./local.nix else {};
      cudaSupport = if localConfig ? cudaSupport then localConfig.cudaSupport else false;
      
      # Detect the current platform
      isLinux = pkgs.stdenv.isLinux;
      isDarwin = pkgs.stdenv.isDarwin;
      
      # Define common packages used across all platforms
      commonPackages = with pkgs; [
        python311
        python311.pkgs.pip
        python311.pkgs.virtualenv
        cmake
        ninja
        gcc
        git
        zlib
        stdenv.cc.cc.lib
        figlet
      ];
      
      # Create a shell script to set up the development environment
      runScript = pkgs.writeShellScriptBin "runScript" ''
        set -e
        export NIXPKGS_ALLOW_UNFREE=1
        export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath commonPackages}:$LD_LIBRARY_PATH
        ${if isLinux && cudaSupport then "export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH" else ""}
        figlet "Pipulate"
        echo "Welcome to the Pipulate development environment on ${system}!"
        echo
        echo "- Checking if pip packages are installed..."
        ${if cudaSupport && isLinux then "echo '- CUDA support enabled.'" else ""}
        test -d .venv || ${pkgs.python311.interpreter} -m venv .venv
        set -e  # Exit immediately if a command exits with a non-zero status

        if source .venv/bin/activate && \
           pip install --upgrade pip --quiet && \
           pip install -r requirements.txt --quiet; then
            package_count=$(pip list --format=freeze | wc -l)
            echo "- Done. $package_count pip packages installed."
        else
            echo "Warning: An error occurred during setup."
        fi
        # Check if numpy is importable (the lyncpin to know if the environment is ready)
        echo "- Checking if numpy is importable..."
        if python -c "import numpy" 2>/dev/null; then
          echo "- numpy is importable (good to go!)"
          echo
          echo "- Start JupyterLab and FastHTML server with: start"
          echo "- Stop JupyterLab and FastHTML server with: stop"
          echo "- To exit the Pipulate environment, type 'exit' twice."
          echo
        else
          echo "Error: numpy could not be imported. Check your installation."
        fi
        
        # Check for Ollama server
        echo "Checking Ollama connectivity..."
        ollama_response=$(python ollama_check.py)
        echo "Ollama says: $ollama_response"
        echo

        echo "Learn more at https://pipulate.com <--Ctrl+Click"
        
        # Create the start script
        cat << EOF > .venv/bin/start
        #!/bin/sh
        stop
        echo "Starting JupyterLab and server..."
        jupyter lab > jupyter.log 2>&1 &
        python server.py > server.log 2>&1 &
        echo "JupyterLab and server started in the background."
        echo "JupyterLab log: jupyter.log"
        echo "Server log: server.log"
        sleep 2
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open "http://localhost:5001" > /dev/null 2>&1 &
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            open "http://localhost:5001" > /dev/null 2>&1 &
        else
            echo "Unsupported OS."
        fi
        EOF
        chmod +x .venv/bin/start

        # Create the stop script
        cat << EOF > .venv/bin/stop
        #!/bin/sh
        echo "Stopping JupyterLab, Jupyter kernels, and server..."
        pkill -f "jupyter-lab"
        pkill -f "ipykernel_launcher"
        pkill -f "python server.py"
        echo "Waiting for processes to terminate..."
        sleep 2
        if pgrep -f "jupyter-lab" > /dev/null || pgrep -f "ipykernel_launcher" > /dev/null || pgrep -f "python server.py" > /dev/null; then
          echo "Some processes are still running. Forcefully terminating..."
          pkill -9 -f "jupyter-lab"
          pkill -9 -f "ipykernel_launcher"
          pkill -9 -f "python server.py"
        fi
        echo "All processes have been stopped."
        EOF
        chmod +x .venv/bin/stop

        # Override PROMPT_COMMAND and set custom PS1
        export PROMPT_COMMAND=""
        PS1='$(printf "\033[01;34m(%s)\033[00m \033[01;32m[%s@%s:%s]$\033[00m " "$(basename "$VIRTUAL_ENV")" "\u" "\h" "\w")'
        export PS1       
        exec bash --norc --noprofile
      '';
      
      # Define the development shell for Linux systems
      linuxDevShell = pkgs.mkShell {
        buildInputs = commonPackages ++ (with pkgs; [
          pythonManylinuxPackages.manylinux2014Package
          stdenv.cc.cc.lib
        ]) ++ pkgs.lib.optionals (cudaSupport && system == "x86_64-linux") (with pkgs; [
          cudatoolkit
          cudnn
          (ollama.override { acceleration = "cuda"; })
        ]);
        shellHook = ''
          ${runScript}/bin/runScript
          # Set up Nix prompt for when user exits Python venv
          nix_prompt='\[\033[1;34m\][nix-dev]\[\033[0m\] \w $ '
          if [ -n "$ZSH_VERSION" ]; then
            setopt PROMPT_SUBST
            PS1="%F{blue}[nix-dev]%f %~ $ "
          else
            PS1="$nix_prompt"
          fi
        '';
      };
      
      # Define the development shell for Darwin (macOS) systems
      darwinDevShell = pkgs.mkShell {
        buildInputs = commonPackages;
        shellHook = ''
          ${runScript}/bin/runScript
          # Set up Nix prompt for when user exits Python venv
          if [ -n "$ZSH_VERSION" ]; then
            setopt PROMPT_SUBST
            PS1="%F{blue}[nix-dev]%f %~ $ "
          else
            PS1='\[\033[1;34m\][nix-dev]\[\033[0m\] \w $ '
          fi
        '';
      };
    in {
      # Choose the appropriate devShell based on the current platform
      devShell = if isLinux then linuxDevShell else darwinDevShell;
    });
}
