{
  description = "Pipulate JupyterLab Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.05";  # Use a stable NixOS release
    flake-utils.url = "github:numtide/flake-utils";     # Utility functions for flakes
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python311;  # Choose your Python version
      pythonPackages = python.pkgs;
    in
    {
      devShell = pkgs.mkShell {
        buildInputs = with pythonPackages; [
          jupyterlab
          numpy
          pandas
          matplotlib
          # Add other Python packages as needed
        ];
        shellHook = ''
          echo "Welcome to the Pipulate JupyterLab environment!"
        '';
      };
    });
}

