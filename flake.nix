{
  # pipulate/flake.nix
  description = "Pipulate Development Environment with python-fasthtml";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-darwin" ];
      forAllSystems = f: builtins.listToAttrs (map (system: { name = system; value = f system; }) systems);
      # Import local configuration if present
      localConfig = if builtins.pathExists ./local.nix then import ./local.nix else {};
      # Use the ? operator to check for cudaSupport
      cudaSupport = if localConfig ? cudaSupport then localConfig.cudaSupport else false;
    in
    {
      devShells = forAllSystems (system: {
        default = let
          pkgs = import nixpkgs { inherit system; config.allowUnfree = true; };
          lib = pkgs.lib;
          # CUDA-specific packages (only on your system)
          cudaPackages = lib.optionals (cudaSupport && system == "x86_64-linux") (with pkgs; [
            pkgs.cudatoolkit
            pkgs.cudnn
            (pkgs.ollama.override { acceleration = "cuda"; })
          ]);
          # Define Python package set
          ps = pkgs.python311Packages;
          # Conditionally override PyTorch for CUDA support
          pytorchPackage = if cudaSupport && system == "x86_64-linux" then
            ps.pytorch.override { cudaSupport = true; }
          else if system == "aarch64-darwin" then
            ps.pytorch-bin
          else
            ps.pytorch;
          # Python packages including JupyterLab and others
          pythonPackages = pkgs.python311.withPackages (ps: [
            ps.jupyterlab
            ps.pandas
            ps.requests
            ps.sqlitedict
            ps.numpy
            ps.matplotlib
            ps.nbdev
            ps.fastapi   # For web applications
            ps.simplenote
            pytorchPackage
            ps.pip  # Include pip for installing python-fasthtml
          ]);
          # Common development tools
          devTools = with pkgs; [
            git
            neovim
            # Add other development tools if needed
          ];
        in pkgs.mkShell {
          buildInputs = devTools ++ [ pythonPackages ] ++ cudaPackages ++ [ pkgs.gcc-libs ];

          shellHook = ''
            export NIXPKGS_ALLOW_UNFREE=1
            echo "Welcome to the Pipulate development environment on ${system}!"
            ${if cudaSupport then "echo 'CUDA support enabled.'" else ""}
            
            # Create a virtual environment if it doesn't exist
            if [ ! -d .venv ]; then
              ${pythonPackages.python.interpreter} -m venv .venv
            fi
            
            # Activate the virtual environment
            source .venv/bin/activate
            
            # Install python-fasthtml if not already installed
            if ! python -c "import fasthtml" 2>/dev/null; then
              echo "Installing python-fasthtml..."
              pip install python-fasthtml > /dev/null 2>&1
              if [ $? -eq 0 ]; then
                echo "python-fasthtml installed successfully."
              else
                echo "Failed to install python-fasthtml. Please check your internet connection and try again."
              fi
            else
              echo "python-fasthtml is already installed."
            fi
            
            echo "Development environment is ready!"

            # === Start Jupyter Lab and Python Server ===

            # Start Jupyter Lab in the background
            echo "Starting Jupyter Lab..."
            jupyter lab &
            JUPYTER_PID=$!

            # Start Python server in the background
            echo "Starting Python server..."
            python server.py &
            SERVER_PID=$!

            # Function to handle cleanup on exit
            cleanup() {
              echo "Stopping Jupyter Lab..."
              kill $JUPYTER_PID

              echo "Stopping Python server..."
              kill $SERVER_PID
            }

            # Trap the EXIT signal to trigger cleanup
            trap cleanup EXIT
          '';
        };
      });
    };
}
