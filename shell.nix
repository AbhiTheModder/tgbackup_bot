{
  pkgs ? import <nixpkgs> { },
}:

let
  pyrogram = pkgs.python3Packages.buildPythonPackage rec {
    pname = "pyrofork";
    version = "2.3.68";
    pyproject = true;
    build-system = [ pkgs.python3Packages.hatchling ];

    src = pkgs.python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "sha256-EtzHt40hebThP9vjESHZI1xL8AibyUbEft5iZH8ZIp8=";
    };

    prePatch = ''
      substituteInPlace pyproject.toml \
      --replace-warn 'pymediainfo-pyrofork>=6.0.1,<7.0.0' 'pymediainfo'
    '';

    propagatedBuildInputs = with pkgs.python3Packages; [
      pyaes
      pymediainfo
      pysocks
    ];
  };

  python = pkgs.python3.withPackages (ps: [
    pyrogram
    pkgs.python3Packages.tgcrypto
  ]);
in

pkgs.mkShell {
  buildInputs = [ python ];
}
