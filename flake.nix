{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = inputs @ { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
      localConfig = if builtins.pathExists ./local.nix then import ./local.nix else {};
      cudaSupport = if localConfig ? cudaSupport then localConfig.cudaSupport else false;
      
      cudaPackages = pkgs.lib.optionals (cudaSupport && system == "x86_64-linux") (with pkgs; [
        cudatoolkit
        cudnn
        (ollama.override { acceleration = "cuda"; })
      ]);
      
      envWithScript = script:
        (pkgs.buildFHSUserEnv {
          name = "python-env";
          targetPkgs = pkgs: (with pkgs; [
            python311
            python311.pkgs.pip
            python311.pkgs.virtualenv
            pythonManylinuxPackages.manylinux2014Package
            cmake
            ninja
            gcc
            git
            stdenv.cc.cc.lib
          ] ++ cudaPackages);
          runScript = "${pkgs.writeShellScriptBin "runScript" (''
            set -e
            export NIXPKGS_ALLOW_UNFREE=1
            export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
            echo "Welcome to the Pipulate development environment on ${system}!"
            ${if cudaSupport then "echo 'CUDA support enabled.'" else ""}
            test -d .venv || ${pkgs.python311.interpreter} -m venv .venv
            source .venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
            ${script}
          '')}/bin/runScript";
        })
        .env;
    in {
      devShell = envWithScript "bash";
    });
}