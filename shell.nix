{
  pkgs ? import <nixpkgs> { },
}:

let
  pyrogram = pkgs.python3Packages.buildPythonPackage rec {
    pname = "pyrofork";
    version = "2.3.69";
    pyproject = true;
    build-system = [ pkgs.python3Packages.hatchling ];

    src = pkgs.python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "sha256-lFsw1QsxgZqQN0mCXidIrFpq8eBzv5fajFPlEP8+1Y0=";
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
