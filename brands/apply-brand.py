#!/usr/bin/env python3
"""
apply-brand.py <brand.toml> [--tree <path>]

Prepares a RustDesk source tree for a specific brand:
  - replaces "RustDesk" brand strings in src/lang/*.rs with the display name
  - sets powered_by_me per locale
  - patches Cargo.toml ProductName / FileDescription
  - patches flutter/windows/runner/Runner.rc
  - copies the brand icon over res/icon.ico + flutter app_icon.ico
The server/key/password/APP_NAME come from OTS_* env vars at *compile* time
(see load_custom_client / config.rs), so this script only touches
display-level assets. Emits an env file to source before `cargo`/`build.py`.
"""
import sys, os, re, shutil, tomllib, pathlib

def load(path):
    with open(path, "rb") as f:
        return tomllib.load(f)

def main():
    if len(sys.argv) < 2:
        print("usage: apply-brand.py <brand.toml> [--tree <path>]"); sys.exit(1)
    manifest = load(sys.argv[1])
    tree = "."
    if "--tree" in sys.argv:
        tree = sys.argv[sys.argv.index("--tree")+1]
    tree = pathlib.Path(tree).resolve()
    ident = manifest["identity"]; srv = manifest["server"]; sec = manifest["secrets"]
    disp = ident["display_name"]

    # 1) brand strings in lang files: RustDesk -> display_name
    lang_dir = tree/"src"/"lang"
    n=0
    for f in lang_dir.glob("*.rs"):
        t=f.read_text(encoding="utf-8")
        orig=t
        # powered_by_me per locale
        if f.name=="ru.rs":
            t=re.sub(r'\("powered_by_me", "[^"]*"\)', f'("powered_by_me", "{ident["powered_by_ru"]}")', t)
        else:
            t=re.sub(r'\("powered_by_me", "[^"]*"\)', f'("powered_by_me", "{ident["powered_by_en"]}")', t)
        # generic RustDesk -> display name inside quoted strings only
        t=t.replace("RustDesk", disp)
        if t!=orig:
            f.write_text(t,encoding="utf-8",newline=""); n+=1
    print(f"lang files branded: {n}")

    # 2) Cargo.toml product metadata
    cargo=tree/"Cargo.toml"
    c=cargo.read_text(encoding="utf-8")
    c=re.sub(r'ProductName\s*=\s*"[^"]*"', f'ProductName = "{ident["product_name"]}"', c)
    c=re.sub(r'FileDescription\s*=\s*"[^"]*"', f'FileDescription = "{ident["file_desc"]}"', c)
    cargo.write_text(c,encoding="utf-8",newline="")
    print("Cargo.toml metadata set")

    # 3) Runner.rc
    rc=tree/"flutter"/"windows"/"runner"/"Runner.rc"
    if rc.exists():
        r=rc.read_text(encoding="utf-8",errors="ignore")
        r=re.sub(r'VALUE "FileDescription", "[^"]*"', f'VALUE "FileDescription", "{ident["file_desc"]}"', r)
        r=re.sub(r'VALUE "ProductName", "[^"]*"', f'VALUE "ProductName", "{ident["product_name"]}"', r)
        rc.write_text(r,encoding="utf-8",newline="")
        print("Runner.rc set")

    # 4) icon
    icon_src=(pathlib.Path(sys.argv[1]).parent/ident.get("app_name","")).parent
    icon_rel=manifest["assets"]["icon_ico"]
    icon_path=(pathlib.Path(sys.argv[1]).parent/icon_rel).resolve()
    if icon_path.exists():
        for dst in [tree/"res"/"icon.ico",
                    tree/"flutter"/"windows"/"runner"/"resources"/"app_icon.ico"]:
            if dst.parent.exists():
                shutil.copy(icon_path, dst); print(f"icon -> {dst}")
    else:
        print(f"WARN: icon not found: {icon_path}")

    # 5) compile-time env file
    envf=tree/".brand-env"
    envf.write_text(
        f'export OTS_APP_NAME="{ident["app_name"]}"\n'
        f'export OTS_RENDEZVOUS="{srv["rendezvous"]}"\n'
        f'export OTS_API_SERVER="{srv["api"]}"\n'
        f'export OTS_SERVER_KEY="{srv["key"]}"\n'
        f'export OTS_CLIENT_PASSWORD="{sec["password"]}"\n',
        encoding="utf-8")
    print(f"env written: {envf}")
    print("=== brand applied:", disp, "===")

if __name__=="__main__":
    main()
