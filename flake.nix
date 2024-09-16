{
  description = "Minimal Python Development Environment for Linux and macOS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05"; # Adjust based on your NixOS channel version
  };

  outputs = { self, nixpkgs, ... }: let
    # Define the systems you want to support
    systems = [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin" # For Apple Silicon Macs
    ];
  in {
    devShells = builtins.listToAttrs (map (system: {
      name = system;
      value = {
        default = nixpkgs.legacyPackages.${system}.mkShell {
          buildInputs = [
            nixpkgs.legacyPackages.${system}.python311  # Include Python 3.11
          ];
        };
      };
    }) systems);
  };
}
