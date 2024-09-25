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
      
      isLinux = pkgs.stdenv.isLinux;
      isDarwin = pkgs.stdenv.isDarwin;
      
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
      
      runScript = pkgs.writeShellScriptBin "runScript" ''
        set -e
        export NIXPKGS_ALLOW_UNFREE=1
        export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath commonPackages}:$LD_LIBRARY_PATH
        ${if isLinux && cudaSupport then "export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH" else ""}
        figlet "Pipulate"
        echo "Welcome to the Pipulate development environment on ${system}!"
        echo "Checking if pip packages are installed..."
        ${if cudaSupport && isLinux then "echo 'CUDA support enabled.'" else ""}
        test -d .venv || ${pkgs.python311.interpreter} -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip --quiet
        pip install -r requirements.txt --quiet
        echo "Done."
        # Check if numpy is importable
        echo "Checking if numpy is importable..."
        if python -c "import numpy" 2>/dev/null; then
          echo "numpy is successfully imported!"
        else
          echo "Error: numpy could not be imported. Check your installation."
        fi
        
        # Override PROMPT_COMMAND and set custom PS1
        export PROMPT_COMMAND=""
        PS1='$(printf "\033[01;34m(%s)\033[00m \033[01;32m[%s@%s:%s]$\033[00m " "$(basename "$VIRTUAL_ENV")" "\u" "\h" "\w")'
        export PS1       
        exec bash --norc --noprofile
      '';
      
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
      devShell = if isLinux then linuxDevShell else darwinDevShell;
    });
}

        
