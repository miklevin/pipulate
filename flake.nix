{
  description = "Pipulate Development Environment with python-fasthtml and jupyter_ai";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-darwin" ];
      forAllSystems = f: builtins.listToAttrs (map (system: { name = system; value = f system; }) systems);
      localConfig = if builtins.pathExists ./local.nix then import ./local.nix else {};
      cudaSupport = if localConfig ? cudaSupport then localConfig.cudaSupport else false;
    in
    {
      devShells = forAllSystems (system: {
        default = let
          pkgs = import nixpkgs { inherit system; config.allowUnfree = true; };
          lib = pkgs.lib;
          cudaPackages = lib.optionals (cudaSupport && system == "x86_64-linux") (with pkgs; [
            pkgs.cudatoolkit
            pkgs.cudnn
            (pkgs.ollama.override { acceleration = "cuda"; })
          ]);
          ps = pkgs.python311Packages;
          pytorchPackage = if cudaSupport && system == "x86_64-linux" then
            ps.pytorch.override { cudaSupport = true; }
          else if system == "aarch64-darwin" then
            ps.pytorch-bin
          else
            ps.pytorch;
          pythonPackages = pkgs.python311.withPackages (ps: [
            ps.jupyterlab
            ps.pandas
            ps.requests
            ps.sqlitedict
            ps.numpy
            ps.matplotlib
            ps.nbdev
            ps.fastapi
            ps.simplenote
            pytorchPackage
            ps.pip
          ]);
          devTools = with pkgs; [
            git
          ];
        in pkgs.mkShell {
          buildInputs = devTools ++ [ pythonPackages ] ++ cudaPackages ++ [
            pkgs.stdenv.cc.cc.lib
          ];

          shellHook = ''
            export NIXPKGS_ALLOW_UNFREE=1
            export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
            echo "Welcome to the Pipulate development environment on ${system}!"
            ${if cudaSupport then "echo 'CUDA support enabled.'" else ""}
            
            if [ ! -d .venv ]; then
              ${pythonPackages.python.interpreter} -m venv .venv
            fi
            
            source .venv/bin/activate
            
            # Function to check and install a package
            check_and_install() {
              package=$1
              if ! python -c "import $package" 2>/dev/null; then
                echo "Installing $package..."
                pip install $package > /dev/null 2>&1
                if [ $? -eq 0 ]; then
                  echo "$package installed successfully."
                else
                  echo "Failed to install $package. Please check your internet connection and try again."
                fi
              else
                echo "$package is already installed."
              fi
            }

            # Check and install nbdev
            check_and_install nbdev
            
            # Check and install python-fasthtml
            check_and_install python-fasthtml
            
            # Check and install jupyter_ai
            check_and_install jupyter_ai
            
            echo "Development environment is ready!"

            # === Start Jupyter Lab and Python Server ===

            echo "Starting Jupyter Lab..."
            jupyter lab &
            JUPYTER_PID=$!

            echo "Starting Python server..."
            python server.py &
            SERVER_PID=$!

            cleanup() {
              echo "Stopping Jupyter Lab..."
              kill $JUPYTER_PID

              echo "Stopping Python server..."
              kill $SERVER_PID
            }

            trap cleanup EXIT
          '';
        };
      });
    };
}
