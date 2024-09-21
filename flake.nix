{
  # This line provides a brief description of what this Nix flake does
  description = "Pipulate Development Environment with python-fasthtml and jupyter_ai";

  # The 'inputs' section specifies the dependencies for this flake
  inputs = {
    # We're using the nixpkgs repository from GitHub, specifically the nixos-24.05 branch
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  };

  # The 'outputs' function defines what this flake produces
  outputs = { self, nixpkgs }:
    let
      # Define the systems this flake supports (x86_64 Linux and ARM64 macOS)
      systems = [ "x86_64-linux" "aarch64-darwin" ];

      # This function allows us to create outputs for all supported systems
      forAllSystems = f: builtins.listToAttrs (map (system: { name = system; value = f system; }) systems);

      # Try to import a local configuration file if it exists, otherwise use an empty set
      localConfig = if builtins.pathExists ./local.nix then import ./local.nix else {};

      # Determine if CUDA support should be enabled based on local configuration
      cudaSupport = if localConfig ? cudaSupport then localConfig.cudaSupport else false;
    in
    {
      # Define development shells for each supported system
      devShells = forAllSystems (system: {
        default = let
          # Import the Nix packages for the current system, allowing unfree packages
          pkgs = import nixpkgs { inherit system; config.allowUnfree = true; };
          lib = pkgs.lib;

          # Include CUDA packages if CUDA support is enabled and we're on x86_64 Linux
          cudaPackages = lib.optionals (cudaSupport && system == "x86_64-linux") (with pkgs; [
            pkgs.cudatoolkit
            pkgs.cudnn
            (pkgs.ollama.override { acceleration = "cuda"; })
          ]);

          # Use Python 3.11 packages
          ps = pkgs.python311Packages;

          # Choose the appropriate PyTorch package based on system and CUDA support
          pytorchPackage = if cudaSupport && system == "x86_64-linux" then
            ps.pytorch.override { cudaSupport = true; }
          else if system == "aarch64-darwin" then
            ps.pytorch-bin
          else
            ps.pytorch;

          # Define the Python environment with required packages
          pythonPackages = pkgs.python311.withPackages (ps: [
            ps.jupyterlab
            # ps.jupyter-lsp  # provides the backend support for LSP
            # ps.jupyterlab-lsp  # integrates LSP features into the JupyterLab user interface
            # ps.python-lsp-server  # a Python implementation of the Language Server Protocol
            ps.pandas
            ps.requests
            ps.sqlitedict
            ps.numpy
            ps.matplotlib
            ps.nbdev
            ps.fastapi
            pytorchPackage  # Not prefixed with .ps because of conditional logic
            ps.pip
          ]);

          # Define development tools
          devTools = with pkgs; [
            git
          ];
        in pkgs.mkShell {
          # Combine all required packages into the shell's build inputs
          buildInputs = devTools ++ [ pythonPackages ] ++ cudaPackages ++ [
            pkgs.stdenv.cc.cc.lib
            # pkgs.nodejs
          ];

          # Define the shell hook that runs when entering the development environment
          shellHook = ''
            # Allow unfree packages (necessary for some CUDA components)
            export NIXPKGS_ALLOW_UNFREE=1

            # Set up the LD_LIBRARY_PATH for C++ libraries
            export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH

            echo "Welcome to the Pipulate development environment on ${system}!"
            ${if cudaSupport then "echo 'CUDA support enabled.'" else ""}
            
            # Create a Python virtual environment if it doesn't exist
            if [ ! -d .venv ]; then
              ${pythonPackages.python.interpreter} -m venv .venv
            fi
            
            # Activate the virtual environment
            source .venv/bin/activate
            
            # Function to check if a Python package is installed and install it if not
            check_and_install() {
              package=$1
              import_name=$2
              if ! python -c "import $import_name" 2>/dev/null; then
                echo "Installing $package..."
                pip install --upgrade $package > /dev/null 2>&1
                if [ $? -eq 0 ]; then
                  echo "$package installed successfully."
                else
                  echo "Failed to install $package. Please check your internet connection and try again."
                fi
              else
                echo "$import_name is already installed."
              fi
            }

            # Check and install required Python packages not yet packaged for nix 
            check_and_install python-fasthtml fasthtml
            check_and_install jupyter_ai jupyter_ai

            echo "Development environment is ready!"

            # Start Jupyter Lab and Python Server
            echo "Starting Jupyter Lab..."
            jupyter lab &
            JUPYTER_PID=$!
            echo "Starting Python server..."
            python server.py &
            SERVER_PID=$!

            # Function to clean up processes on exit
            cleanup() {
              echo "Stopping Jupyter Lab..."
              kill $JUPYTER_PID
              echo "Stopping Python server..."
              kill $SERVER_PID
            }

            # Set up trap to call cleanup function on exit
            trap cleanup EXIT
          '';
        };
      });
    };
}
