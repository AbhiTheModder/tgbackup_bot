{
  pkgs ? import <nixpkgs> { },
}:

let
  telethon = pkgs.python3Packages.telethon.overrideAttrs (oldAttrs: {
    version = "1.40.0";
    src = pkgs.python3Packages.fetchPypi {
      pname = "telethon";
      version = "1.40.0";
      sha256 = "sha256-QOgzJod6Lmi3VNS20NHKWskkEQBFsDngJmDy1nrdl9s=";
    };
    doCheck = false;

    checkPhase = "echo skipping tests";
    installCheckPhase = "echo skipping install check";
    pytestCheckPhase = "echo skipping pytest check";
  });

  python = pkgs.python3.withPackages (ps: [ telethon ]);
in

pkgs.mkShell {
  buildInputs = [ python ];
}
